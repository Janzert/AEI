import http.cookiejar
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from configparser import ConfigParser
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl

from pyrimaa import invite_controller
from pyrimaa.invite_controller import (
    Controller,
    Lobby,
    LobbyError,
    Policy,
    entries,
    invites_on,
    normalize_tc,
)

GR_URL = "http://arimaa.example/arimaa/gameroom"

CONFIG = f"""
[global]
gameroom_url = {GR_URL}
default_engine = bot_a

[invites]
timecontrols = 30s/2m/100/0/10m, 1m/5m/100/0/30m
rated = unrated
max_games = 2

[bot_b.invites]
timecontrols = 2m/2m/100/0/20m
rated = both
"""


def make_config(text=CONFIG):
    config = ConfigParser()
    config.read_string(text)
    return config


def invitation(created, timecontrol="30s/2m/100/0/10m", rated="0", side="b"):
    """An invitedmegames entry as the lobby's state sends it."""
    return {
        "invitor": "21487",
        "invited": "19377",
        "createdts": created,
        "status": "i",
        "reason": "",
        "invitorside": side,
        "timecontrol": timecontrol,
        "rated": rated,
        "opponent": {"username": "Inviter", "id": "21487", "type": "h"},
    }


def sid_cookie(value):
    return http.cookiejar.Cookie(
        0, "sid", value, None, False, "arimaa.example", True, False, "/",
        True, False, None, False, None, None, {},
    )  # fmt: skip


class FakeResponse(io.BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body.encode("utf-8"))
        self.status = status


def redirect(url):
    return HTTPError(url, 302, "Found", {}, io.BytesIO(b"<p>moved</p>"))


class FakeOpener:
    """Stands in for the lobby's url opener.

    `replies` maps a CGI name to a reply body, an exception instance to
    raise, or a function of the request returning either.
    """

    def __init__(self, replies):
        self.replies = replies
        self.requests = []

    def open(self, req, timeout=None):
        self.requests.append(req)
        cgi = req.full_url.split("?")[0].rsplit("/", 1)[1]
        reply = self.replies[cgi]
        if callable(reply):
            reply = reply(req)
        if isinstance(reply, Exception):
            raise reply
        return FakeResponse(reply)

    def form(self, index):
        return dict(parse_qsl(self.requests[index].data.decode("utf-8")))


def fake_lobby(replies):
    lobby = Lobby(GR_URL)
    lobby.opener = FakeOpener(replies)
    return lobby


class HelpersTest(unittest.TestCase):
    def test_entries_from_list_or_object(self):
        self.assertEqual(entries({"a": [{"x": 1}, "junk"]}, "a"), [{"x": 1}])
        self.assertEqual(entries({"a": {"1": {"x": 1}}}, "a"), [{"x": 1}])
        self.assertEqual(entries({"a": ""}, "a"), [])
        self.assertEqual(entries({}, "a"), [])

    def test_invites_on(self):
        def state(inviteme, **me):
            online = [
                {"id": "1", "username": "Other", "inviteme": "1"},
                {"id": "19377", "username": "bot_A", "inviteme": inviteme},
            ]
            return {"online": online, **({"me": me} if me else {})}

        self.assertTrue(invites_on(state("1"), "bot_a"))
        self.assertTrue(invites_on(state("1 "), "bot_a"))
        self.assertTrue(invites_on(state("2 "), "bot_a"))
        self.assertFalse(invites_on(state(""), "bot_a"))
        self.assertFalse(invites_on(state("x"), "bot_a"))
        # The login name may be an email address; "me" names the user.
        self.assertFalse(invites_on(state("", id="19377"), "bot@example.com"))
        self.assertIsNone(invites_on(state("1"), "bot@example.com"))
        self.assertIsNone(invites_on({}, "bot_a"))

    def test_normalize_tc(self):
        self.assertEqual(normalize_tc(" 30S/2m/100/0/10M "), "30s/2m/100/0/10m")


class LobbyTest(unittest.TestCase):
    def test_login_takes_sid_cookie(self):
        lobby = fake_lobby({})

        def login(req):
            lobby.cookies.set_cookie(sid_cookie("abc"))
            return redirect(req.full_url)

        lobby.opener.replies["login.cgi"] = login
        lobby.login("bot_x", "secret")
        self.assertEqual(lobby.sid, "abc")
        req = lobby.opener.requests[0]
        self.assertEqual(req.get_header("Referer"), GR_URL + "/login.cgi")
        self.assertEqual(
            lobby.opener.form(0),
            {"email": "bot_x", "password": "secret", "timezone": "0"},
        )

    def test_login_refused(self):
        lobby = fake_lobby({"login.cgi": "<html><b>Bad password</b></html>"})
        with self.assertRaisesRegex(LobbyError, "login refused: Bad password"):
            lobby.login("bot_x", "wrong")
        self.assertIsNone(lobby.sid)

    def test_state_sends_json(self):
        lobby = fake_lobby({"client2gr.cgi": '{"invitedmegames": []}'})
        lobby.sid = "abc"
        self.assertEqual(lobby.state(), {"invitedmegames": []})
        body = json.loads(lobby.opener.requests[0].data)
        self.assertEqual(body, {"action": "state", "sid": "abc"})

    def test_state_errors(self):
        for reply, message in [
            ('{"error": "Gameroom: login expired"}', "login expired"),
            ("not json", "bad state reply"),
            ("[1]", "bad state reply"),
        ]:
            lobby = fake_lobby({"client2gr.cgi": reply})
            with self.assertRaisesRegex(LobbyError, message):
                lobby.state()

    def test_refused_and_network_errors(self):
        url = GR_URL + "/client2gr.cgi"
        for error, message in [
            (HTTPError(url, 404, "Not Found", {}, io.BytesIO()), r"refused.*404"),
            (HTTPError(url, 500, "Error", {}, io.BytesIO()), "HTTP 500"),
            (URLError("down"), "network error"),
        ]:
            lobby = fake_lobby({"client2gr.cgi": error})
            with self.assertRaisesRegex(LobbyError, message):
                lobby.state()

    def test_accept(self):
        lobby = fake_lobby({"acceptInvite.cgi": redirect(GR_URL)})
        lobby.accept("21487", "1792223814")
        req = lobby.opener.requests[0]
        self.assertEqual(
            req.full_url, GR_URL + "/acceptInvite.cgi?id=21487&ts=1792223814"
        )
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("Referer"), GR_URL + "/acceptInvite.cgi")
        # The page a browser sees also counts.
        fake_lobby({"acceptInvite.cgi": "You have accepted"}).accept("1", "2")
        lobby = fake_lobby({"acceptInvite.cgi": "<p>No such invitation</p>"})
        with self.assertRaisesRegex(LobbyError, "No such invitation"):
            lobby.accept("1", "2")

    def test_decline(self):
        lobby = fake_lobby({"declineInvite.cgi": redirect(GR_URL)})
        lobby.decline("21487", "1792223814", "Busy.")
        self.assertEqual(
            lobby.opener.form(0),
            {"reason": "Busy.", "id": "21487", "ts": "1792223814"},
        )
        fake_lobby({"declineInvite.cgi": "Game Declined"}).decline("1", "2", "r")
        lobby = fake_lobby({"declineInvite.cgi": "<p>Error</p>"})
        with self.assertRaisesRegex(LobbyError, "decline failed"):
            lobby.decline("1", "2", "r")

    def test_set_invites(self):
        lobby = fake_lobby({"inviteMe.cgi": "<b>Currently  not seeking invites.</b>"})
        lobby.set_invites(False)
        self.assertEqual(lobby.opener.form(0), {"noinvite": "Update"})
        lobby = fake_lobby({"inviteMe.cgi": "<b>Currently  seeking invites.</b>"})
        lobby.set_invites(True)
        self.assertEqual(lobby.opener.form(0), {"yesinvite": "Update"})
        lobby = fake_lobby({"inviteMe.cgi": "<b>Currently  seeking invites.</b>"})
        with self.assertRaisesRegex(LobbyError, "setting invitations failed"):
            lobby.set_invites(False)


class PolicyTest(unittest.TestCase):
    def test_global_settings(self):
        policy = Policy(make_config(), "bot_a")
        self.assertEqual(policy.timecontrols, ["30s/2m/100/0/10m", "1m/5m/100/0/30m"])
        self.assertEqual(policy.rated, "unrated")
        self.assertEqual(policy.max_games, 2)
        self.assertEqual(policy.poll_interval, 25)

    def test_bot_section_overrides_each_setting(self):
        policy = Policy(make_config(), "bot_b")
        self.assertEqual(policy.timecontrols, ["2m/2m/100/0/20m"])
        self.assertEqual(policy.rated, "both")
        self.assertEqual(policy.max_games, 2)

    def test_bot_section_alone(self):
        config = make_config(
            "[bot_c.invites]\ntimecontrols = 2m/2m/100/0/20m\n"
            "  1m/5m/100/0/30m\nrated = rated\npoll_interval = 5\n"
        )
        policy = Policy(config, "bot_c")
        self.assertEqual(policy.timecontrols, ["2m/2m/100/0/20m", "1m/5m/100/0/30m"])
        self.assertEqual(policy.max_games, 1)
        self.assertEqual(policy.poll_interval, 20)
        self.assertEqual(Policy(config, "bot_d").timecontrols, [])

    def test_bad_rated(self):
        config = make_config("[invites]\nrated = sometimes\n")
        with self.assertRaises(ValueError):
            Policy(config, "bot_a")

    def test_refusal(self):
        policy = Policy(make_config(), "bot_a")
        self.assertIsNone(policy.refusal(invitation("1")))
        self.assertIsNone(policy.refusal(invitation("1", "1M/5m/100/0/30m")))
        self.assertIn(
            "30s/2m/100/0/10m", policy.refusal(invitation("1", "2m/2m/100/0/20m"))
        )
        self.assertEqual(
            policy.refusal(invitation("1", rated="1")), "I only play unrated games."
        )
        config = make_config(CONFIG + "[bot_r.invites]\nrated = rated\n")
        self.assertEqual(
            Policy(config, "bot_r").refusal(invitation("1")),
            "I only play rated games.",
        )
        both = Policy(make_config(), "bot_b")
        self.assertIsNone(both.refusal(invitation("1", "2m/2m/100/0/20m", "1")))
        self.assertIsNone(both.refusal(invitation("1", "2m/2m/100/0/20m", "0")))


class FakeProc:
    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.ctl = Controller(make_config(), "bot.cfg", None, "bot_A", "pw")
        self.ctl.lobby = mock.Mock(spec=Lobby)
        self.launched = []
        self.ctl.launch = lambda gid, side: self.launched.append((gid, side))

    def answer(self, *invitations):
        with self.assertLogs("invites", "INFO"):
            self.ctl.answer({"invitedmegames": list(invitations)})

    def test_policy_uses_bot_section(self):
        self.assertEqual(self.ctl.policy.timecontrols[0], "30s/2m/100/0/10m")
        ctl = Controller(make_config(), "bot.cfg", "bot_b", "bot_B", "pw")
        self.assertEqual(ctl.policy.timecontrols, ["2m/2m/100/0/20m"])

    def test_accepts_matching_invitation(self):
        self.answer(invitation("100"))
        self.ctl.lobby.accept.assert_called_once_with("21487", "100")
        self.ctl.lobby.decline.assert_not_called()
        self.assertIn("100", self.ctl.accepted)

    def test_declines_with_reason(self):
        self.answer(invitation("100", rated="1"))
        self.ctl.lobby.decline.assert_called_once_with(
            "21487", "100", "I only play unrated games."
        )
        self.ctl.lobby.accept.assert_not_called()

    def test_answers_each_invitation_once(self):
        self.answer(invitation("100"))
        self.ctl.answer({"invitedmegames": [invitation("100")]})
        self.assertEqual(self.ctl.lobby.accept.call_count, 1)

    def test_declines_beyond_max_games(self):
        self.ctl.games["5"] = FakeProc()
        self.answer(invitation("100"), invitation("101"))
        self.ctl.lobby.accept.assert_called_once_with("21487", "100")
        self.ctl.lobby.decline.assert_called_once()
        self.assertIn("try again later", self.ctl.lobby.decline.call_args[0][2])

    def test_starts_accepted_game_on_its_side(self):
        self.ctl.accepted = {"100": ("Inviter", 0), "101": ("Inviter", 0)}
        with mock.patch("time.time", return_value=10):
            self.ctl.start_accepted(
                {
                    "mygames": [
                        {"id": "7", "createdts": "99", "wusername": "bot_a"},
                        {"id": "8", "createdts": "100", "wusername": "BOT_a"},
                        {"id": "9", "createdts": "101", "wusername": "Inviter"},
                    ]
                }
            )
        self.assertEqual(self.launched, [("8", "w"), ("9", "b")])
        self.assertEqual(self.ctl.accepted, {})

    def test_accepted_game_waits_then_gives_up(self):
        self.ctl.accepted = {"100": ("Inviter", 0)}
        with mock.patch("time.time", return_value=200):
            self.ctl.start_accepted({"mygames": []})
        self.assertIn("100", self.ctl.accepted)
        with mock.patch("time.time", return_value=400):
            with self.assertLogs("invites", "WARNING"):
                self.ctl.start_accepted({"mygames": []})
        self.assertEqual(self.ctl.accepted, {})
        self.assertEqual(self.launched, [])

    def test_reap(self):
        self.ctl.games = {"1": FakeProc(), "2": FakeProc(0)}
        with self.assertLogs("invites", "INFO"):
            self.ctl.reap()
        self.assertEqual(list(self.ctl.games), ["1"])


def online_state(inviteme):
    return {"online": [{"username": "bot_A", "inviteme": inviteme}]}


class InviteFlagTest(unittest.TestCase):
    def setUp(self):
        self.ctl = Controller(make_config(), "bot.cfg", None, "bot_A", "pw")
        self.ctl.lobby = mock.Mock(spec=Lobby)
        self.ctl.lobby.sid = "abc"

    def test_no_change_while_flag_matches(self):
        self.ctl.update_invites(online_state("1"))
        self.ctl.games["5"] = FakeProc()
        self.ctl.update_invites(online_state("1 "))
        self.ctl.lobby.set_invites.assert_not_called()

    def test_off_when_full_and_on_when_free(self):
        self.ctl.games = {"5": FakeProc()}
        self.ctl.accepted = {"100": ("Inviter", 0)}
        with self.assertLogs("invites", "INFO"):
            self.ctl.update_invites(online_state("1"))
        self.ctl.lobby.set_invites.assert_called_once_with(False)
        self.ctl.lobby.set_invites.reset_mock()
        self.ctl.update_invites(online_state(""))
        self.ctl.lobby.set_invites.assert_not_called()
        del self.ctl.games["5"]
        with self.assertLogs("invites", "INFO"):
            self.ctl.update_invites(online_state(""))
        self.ctl.lobby.set_invites.assert_called_once_with(True)

    def test_turns_on_flag_found_off(self):
        with self.assertLogs("invites", "INFO"):
            self.ctl.update_invites(online_state(""))
        self.ctl.lobby.set_invites.assert_called_once_with(True)

    def test_not_listed(self):
        self.ctl.update_invites({"online": []})
        self.ctl.lobby.set_invites.assert_not_called()
        self.ctl.restore_invites()
        self.ctl.lobby.set_invites.assert_not_called()

    def test_restore(self):
        self.ctl.games = {"5": FakeProc(), "6": FakeProc()}
        with self.assertLogs("invites", "INFO"):
            self.ctl.update_invites(online_state("1"))
        self.ctl.lobby.set_invites.reset_mock()
        self.ctl.lobby.sid = None

        def login(user, password):
            self.ctl.lobby.sid = "abc"

        self.ctl.lobby.login.side_effect = login
        with self.assertLogs("invites", "INFO"):
            self.ctl.restore_invites()
        self.ctl.lobby.login.assert_called_once_with("bot_A", "pw")
        self.ctl.lobby.set_invites.assert_called_once_with(True)
        # Already as found: nothing to send.
        self.ctl.restore_invites()
        self.ctl.lobby.set_invites.assert_called_once_with(True)

    def test_restore_unchanged_flag_sends_nothing(self):
        self.ctl.update_invites(online_state("1"))
        self.ctl.restore_invites()
        self.ctl.lobby.set_invites.assert_not_called()

    def test_restore_failure_is_logged(self):
        with self.assertLogs("invites", "INFO"):
            self.ctl.update_invites(online_state(""))
        self.ctl.lobby.set_invites.side_effect = LobbyError("down")
        with self.assertLogs("invites", "WARNING") as logs:
            self.ctl.restore_invites()
        self.assertIn("Could not restore", logs.output[-1])


class LaunchTest(unittest.TestCase):
    def test_launch_args(self):
        for bot, extra in [(None, []), ("bot_b", ["-b", "bot_b"])]:
            ctl = Controller(make_config(), "bot.cfg", bot, "bot_A", "pw")
            with mock.patch("subprocess.Popen") as popen:
                with self.assertLogs("invites", "INFO"):
                    ctl.launch("8", "w")
            popen.assert_called_once_with(
                [sys.executable, "-m", "pyrimaa.gameroom", "-c", "bot.cfg"]
                + extra
                + ["play", "8", "w"]
            )
            self.assertIs(ctl.games["8"], popen.return_value)


class StopLoop(Exception):
    pass


class RunTest(unittest.TestCase):
    def setUp(self):
        self.ctl = Controller(make_config(), "bot.cfg", None, "bot_A", "pw")
        self.ctl.lobby = mock.Mock(spec=Lobby)
        self.ctl.lobby.sid = None
        self.ctl.launch = mock.Mock()
        self.sleeps = []

    def run_polls(self, polls):
        """Runs the loop for `polls` polls (each ends in a sleep)."""

        def sleep(seconds):
            self.sleeps.append(seconds)
            if self.sleeps.count(25) >= polls:
                raise StopLoop

        with mock.patch("time.sleep", sleep), mock.patch("time.time", return_value=0):
            with mock.patch("random.uniform", return_value=0):
                with self.assertRaises(StopLoop):
                    self.ctl.run()

    def test_logs_in_accepts_and_starts_game(self):
        state = {"invitedmegames": [invitation("100")]}
        after = {"mygames": [{"id": "8", "createdts": "100", "wusername": "x"}]}
        self.ctl.lobby.state.side_effect = [state, after]

        def login(user, password):
            self.ctl.lobby.sid = "abc"

        self.ctl.lobby.login.side_effect = login
        with self.assertLogs("invites", "INFO"):
            self.run_polls(1)
        self.ctl.lobby.login.assert_called_once_with("bot_A", "pw")
        self.ctl.lobby.accept.assert_called_once_with("21487", "100")
        self.ctl.launch.assert_called_once_with("8", "b")
        self.assertEqual(self.sleeps, [3, 25])

    def test_logs_in_again_after_error_and_backs_off(self):
        self.ctl.lobby.state.side_effect = LobbyError("login expired")
        with self.assertLogs("invites", "WARNING") as logs:
            self.run_polls(4)
        self.assertEqual(self.ctl.lobby.login.call_count, 4)
        self.assertEqual(len(logs.records), 4)
        self.assertEqual(self.sleeps, [25, 25, 30, 25, 60, 25])

    def test_flag_follows_slots_and_is_restored(self):
        self.ctl.lobby.sid = "abc"
        state = {"invitedmegames": [invitation("100")], **online_state("1")}
        after = {
            "mygames": [{"id": "8", "createdts": "100", "wusername": "x"}],
            **online_state("1"),
        }
        self.ctl.policy.max_games = 1
        self.ctl.lobby.state.side_effect = [state, after]
        self.ctl.launch.side_effect = lambda gid, side: self.ctl.games.update(
            {gid: FakeProc()}
        )
        with self.assertLogs("invites", "INFO"):
            self.run_polls(1)
        self.ctl.lobby.set_invites.assert_called_once_with(False)
        with mock.patch("os.path.exists", return_value=True):
            with self.assertLogs("invites", "INFO"):
                self.assertEqual(self.ctl.run(), 0)
        self.assertEqual(
            self.ctl.lobby.set_invites.call_args_list,
            [mock.call(False), mock.call(True)],
        )

    def test_stop_file(self):
        tmpdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            open("stop_invites", "w").close()
            with self.assertLogs("invites", "INFO"):
                self.assertEqual(self.ctl.run(), 0)
        finally:
            os.chdir(cwd)
            shutil.rmtree(tmpdir)
        self.ctl.lobby.login.assert_not_called()


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.cfg = os.path.join(self.tmpdir, "gameroom.cfg")
        self.addCleanup(self.remove_handlers)

    def remove_handlers(self):
        for handler in list(invite_controller.log.handlers):
            handler.close()
            invite_controller.log.removeHandler(handler)

    def write(self, text):
        with open(self.cfg, "w") as f:
            f.write(text)

    def base(self):
        return (
            f"[global]\ngameroom_url = {GR_URL}\ndefault_engine = bot_a\n"
            "username = bot_A\npassword = pw\n"
            f"[Logging]\ndirectory = {self.tmpdir}\n"
        )

    def test_missing_config(self):
        with mock.patch("builtins.print"):
            self.assertEqual(invite_controller.main(["x", "-c", self.cfg]), 1)

    def test_no_time_controls(self):
        self.write(self.base())
        with mock.patch("builtins.print") as printed:
            self.assertEqual(invite_controller.main(["x", "-c", self.cfg]), 1)
        self.assertIn("[bot_a.invites]", printed.call_args[0][0])

    def test_runs_with_bot_section(self):
        self.write(self.base() + "[bot_b.invites]\ntimecontrols = 2m/2m/100/0/20m\n")
        with mock.patch.object(Controller, "run", return_value=0) as run:
            with mock.patch("logging.StreamHandler.emit"):
                result = invite_controller.main(["x", "-c", self.cfg, "-b", "bot_b"])
        self.assertEqual(result, 0)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
