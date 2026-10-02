import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from configparser import ConfigParser
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl

from pyrimaa import gameroom

GR_URL = "http://arimaa.example/arimaa/gameroom"
LOBBY_URL = GR_URL + "/bot1gr.cgi"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body.encode("utf-8")


class FakeServer:
    """Stands in for urlopen, answering each request with a canned reply.

    `replies` maps an action (or `what`) value to a reply body or to an
    exception instance to raise.
    """

    def __init__(self, replies):
        self.replies = replies
        self.requests = []

    def __call__(self, req):
        values = dict(parse_qsl(req.data.decode("utf-8")))
        self.requests.append((req, values))
        reply = self.replies[values.get("action", values.get("what"))]
        if isinstance(reply, Exception):
            raise reply
        return FakeResponse(reply)

    def actions(self):
        return [v.get("action", v.get("what")) for _, v in self.requests]


def game_entry(gid, side, player):
    """A game list entry as the bot lobby sends it, keyed <gid>:<side>."""
    return f"{gid}:{side}=gid={gid}%13side={side}%13player={player}%13"


def dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", ""])
    proc.wait()
    return proc.pid


class ParseTest(unittest.TestCase):
    def test_unquote(self):
        self.assertEqual(gameroom.unquote("a%13b%25c"), "a\nb%c")

    def test_parsebody(self):
        body = "&junkvar=xxxx\nsid=abc\nnote=1+1=2\nnovalue\n=noname\n--END--\n"
        self.assertEqual(
            gameroom.parsebody(body),
            {"&junkvar": "xxxx", "sid": "abc", "note": "1+1=2"},
        )

    def test_parsebody_nested(self):
        outer = gameroom.parsebody(game_entry("12", "w", "bot_x"))
        self.assertEqual(
            gameroom.parsebody(outer["12:w"]),
            {"gid": "12", "side": "w", "player": "bot_x"},
        )


class ParseArgsTest(unittest.TestCase):
    def test_defaults(self):
        opts = gameroom.parseargs(["gameroom"])
        self.assertEqual(opts["config"], "gameroom.cfg")
        self.assertEqual(opts["against"], "")
        self.assertEqual(opts["side"], "b")
        self.assertFalse(opts["onemove"])

    def test_side_only(self):
        opts = gameroom.parseargs(["gameroom", "-c", "x.cfg", "g"])
        self.assertEqual(opts["config"], "x.cfg")
        self.assertEqual(opts["side"], "g")

    def test_play_and_move(self):
        opts = gameroom.parseargs(["gameroom", "play", "Bot_Foo", "s"])
        self.assertEqual(opts["against"], "bot_foo")
        self.assertEqual(opts["side"], "s")
        self.assertFalse(opts["onemove"])
        opts = gameroom.parseargs(["gameroom", "move", "1234"])
        self.assertEqual(opts["against"], "1234")
        self.assertEqual(opts["side"], "")
        self.assertTrue(opts["onemove"])

    def test_bad_args(self):
        with mock.patch("sys.stdout"):
            self.assertRaises(ValueError, gameroom.parseargs, ["gameroom", "play"])
            self.assertRaises(ValueError, gameroom.parseargs, ["gameroom", "x"])


@mock.patch("pyrimaa.gameroom.time.sleep")
class PostTest(unittest.TestCase):
    def test_sends_referer_and_parses_reply(self, _sleep):
        server = FakeServer({"login": "sid=abc\n--END--\n"})
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            info = gameroom.post(LOBBY_URL, {"action": "login", "username": "u"})
        self.assertEqual(info, {"sid": "abc"})
        req, values = server.requests[0]
        # arimaa.com answers 404 unless the Referer is a gameroom page.
        self.assertEqual(req.get_header("Referer"), LOBBY_URL)
        self.assertEqual(values, {"action": "login", "username": "u"})

    def test_unknown_session_raises(self, _sleep):
        server = FakeServer({"move": "error=Gameserver: Invalid Session Id\n"})
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            with self.assertLogs("gameroom", "ERROR"):
                self.assertRaises(
                    ValueError, gameroom.post, LOBBY_URL, {"action": "move"}
                )

    def test_empty_reply_retried_five_times(self, sleep):
        server = FakeServer({"x": ""})
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            self.assertEqual(gameroom.post(LOBBY_URL, {"action": "x"}), {})
        self.assertEqual(len(server.requests), 5)
        self.assertEqual(sleep.call_count, 4)

    def test_windows_connect_timeout_retried(self, _sleep):
        timeout = URLError(socket.gaierror(10060, "timed out"))
        replies = iter([timeout, timeout, FakeResponse("ok=1\n")])

        def urlopen(req):
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return reply

        with mock.patch("pyrimaa.gameroom.urlopen", urlopen):
            self.assertEqual(gameroom.post(LOBBY_URL, {"action": "x"}), {"ok": "1"})

    def test_other_lookup_error_raised(self, _sleep):
        err = URLError(socket.gaierror(-2, "Name or service not known"))
        server = FakeServer({"x": err})
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            with self.assertRaises(URLError) as ctx:
                gameroom.post(LOBBY_URL, {"action": "x"})
        self.assertIs(ctx.exception, err)
        self.assertEqual(len(server.requests), 1)

    def test_http_error_logged_and_raised(self, _sleep):
        server = FakeServer({"x": HTTPError(LOBBY_URL, 404, "Not Found", {}, None)})
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            with self.assertLogs("gameroom", "ERROR") as logs:
                self.assertRaises(HTTPError, gameroom.post, LOBBY_URL, {"action": "x"})
        self.assertIn("HTTP 404", logs.output[0])
        self.assertIn("refusing", logs.output[0])
        self.assertEqual(len(server.requests), 1)


@mock.patch("pyrimaa.gameroom.time.sleep")
class GameRoomTest(unittest.TestCase):
    def test_url(self, _sleep):
        self.assertEqual(gameroom.GameRoom(GR_URL).url, LOBBY_URL)
        self.assertEqual(gameroom.GameRoom(GR_URL + "/").url, LOBBY_URL)

    def test_login(self, _sleep):
        server = FakeServer({"login": "sid=abc\n"})
        room = gameroom.GameRoom(GR_URL)
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            room.login("bot_x", "pw")
        self.assertEqual(room.sid, "abc")
        _, values = server.requests[0]
        self.assertEqual(values["username"], "bot_x")
        self.assertEqual(values["password"], "pw")

    def test_login_refused(self, _sleep):
        msg = "Gameroom: Problem with Password. Does not match the expected value."
        server = FakeServer({"login": f"error={msg}\n"})
        room = gameroom.GameRoom(GR_URL)
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            with self.assertLogs("gameroom", "ERROR"):
                with self.assertRaises(gameroom.LoginError) as ctx:
                    room.login("bot_x", "wrong")
        self.assertEqual(str(ctx.exception), msg)
        self.assertIsNone(room.sid)

    def test_logout_before_login(self, _sleep):
        room = gameroom.GameRoom(GR_URL)
        with self.assertLogs("gameroom", "WARNING"):
            self.assertEqual(room.logout(), "0")

    def test_game_lists(self, _sleep):
        server = FakeServer(
            {
                "myGames": game_entry("12", "w", "bot_a") + "\nnum=1\n",
                "join": game_entry("13", "b", "bot_b")
                + "\n"
                + game_entry("14", "w", "bot_c")
                + "\nnum=2\n",
            }
        )
        room = gameroom.GameRoom(GR_URL)
        room.sid = "abc"
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            mine = room.mygames()
            open_games = room.opengames()
        self.assertEqual(mine, [{"gid": "12", "side": "w", "player": "bot_a"}])
        self.assertEqual([g["gid"] for g in open_games], ["13", "14"])

    def test_newgame_bad_side(self, _sleep):
        room = gameroom.GameRoom(GR_URL)
        self.assertRaises(ValueError, room.newgame, "g")


class RunFileTest(unittest.TestCase):
    def setUp(self):
        self.run_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.run_dir)

    def write_run_file(self, name, content):
        with open(os.path.join(self.run_dir, name), "w") as f:
            f.write(content)

    def test_touch_and_remove(self):
        with self.assertLogs("gameroom", "INFO"):
            gameroom.touch_run_file(self.run_dir, "5w.bot")
        with open(os.path.join(self.run_dir, "5w.bot")) as f:
            self.assertEqual(int(f.read()), os.getpid())
        with self.assertLogs("gameroom", "INFO"):
            gameroom.remove_run_file(self.run_dir, "5w.bot")
        self.assertEqual(os.listdir(self.run_dir), [])

    def test_how_many_bots(self):
        self.write_run_file("1w.bot", f"{os.getpid()}\n")
        self.write_run_file("2b.bot", f"{os.getpid()}\n")
        self.write_run_file("3w.bot", "not a pid\n")
        self.write_run_file("notes.txt", f"{os.getpid()}\n")
        if sys.platform != "win32":
            self.write_run_file("4w.bot", f"{dead_pid()}\n")
        self.assertEqual(gameroom.how_many_bots(self.run_dir), 2)

    def test_already_playing_live_process(self):
        self.write_run_file("7w.bot", f"{os.getpid()}\n")
        with self.assertLogs("gameroom", "INFO") as logs:
            self.assertTrue(gameroom.already_playing(self.run_dir, "7", "w"))
        self.assertIn("already playing", logs.output[0])

    def test_already_playing_no_run_file(self):
        with mock.patch.object(gameroom.log, "info") as info:
            self.assertFalse(gameroom.already_playing(self.run_dir, "7", "w"))
        info.assert_not_called()

    def test_already_playing_bad_run_file(self):
        self.write_run_file("7w.bot", "not a pid\n")
        self.assertFalse(gameroom.already_playing(self.run_dir, "7", "w"))

    @unittest.skipIf(sys.platform == "win32", "process probe is POSIX only")
    def test_already_playing_dead_process(self):
        self.write_run_file("7w.bot", f"{dead_pid()}\n")
        with mock.patch.object(gameroom.log, "info") as info:
            self.assertFalse(gameroom.already_playing(self.run_dir, "7", "w"))
        info.assert_not_called()


@mock.patch("pyrimaa.gameroom.time.sleep")
class RunGameTest(unittest.TestCase):
    """run_game up to the point of joining, with a fake engine and server."""

    def setUp(self):
        self.run_dir = tempfile.mkdtemp()
        self.config = ConfigParser()
        self.config.read_dict(
            {
                "global": {
                    "gameroom_url": GR_URL,
                    "run_dir": self.run_dir,
                    "max_bots": "2",
                    "default_engine": "bot",
                    "username": "bot_x",
                    "password": "pw",
                },
                "bot": {
                    "cmdline": "unused",
                    "greeting": "hi",
                    "timecontrol": "30s/1m",
                    "rated": "False",
                },
            }
        )
        self.engine_ctl = mock.MagicMock()
        self.engine_ctl.isready.return_value = []
        self.engine_ctl.engine.proc.poll.return_value = 0
        patches = [
            mock.patch("pyrimaa.gameroom.aei.get_engine"),
            mock.patch(
                "pyrimaa.gameroom.aei.EngineController",
                return_value=self.engine_ctl,
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        shutil.rmtree(self.run_dir)

    def run_game(self, server, against="", side="w"):
        options = {"bot": None, "against": against, "side": side, "onemove": False}
        with mock.patch("pyrimaa.gameroom.urlopen", server):
            return gameroom.run_game(options, self.config)

    def test_login_refused(self, _sleep):
        server = FakeServer({"login": "error=Gameroom: Problem with Password.\n"})
        with self.assertLogs("gameroom", "ERROR") as logs:
            self.assertEqual(self.run_game(server), 1)
        self.assertTrue(any("Could not log in as bot_x" in m for m in logs.output))
        self.assertEqual(server.actions(), ["login"])
        self.engine_ctl.quit.assert_called_once()
        self.engine_ctl.cleanup.assert_called_once()

    def test_http_error_at_login(self, _sleep):
        server = FakeServer({"login": HTTPError(LOBBY_URL, 404, "Not Found", {}, None)})
        with self.assertLogs("gameroom", "ERROR") as logs:
            self.assertEqual(self.run_game(server), 1)
        self.assertIn("HTTP 404", logs.output[0])
        self.assertEqual(server.actions(), ["login"])
        self.engine_ctl.quit.assert_called_once()
        self.engine_ctl.cleanup.assert_called_once()

    def test_skips_game_another_process_is_playing(self, _sleep):
        with open(os.path.join(self.run_dir, "12w.bot"), "w") as f:
            f.write(f"{os.getpid()}\n")
        server = FakeServer(
            {
                "login": "sid=abc\n",
                "myGames": game_entry("12", "w", "bot_a") + "\n",
                "join": "num=0\n",
            }
        )
        with self.assertLogs("gameroom", "INFO") as logs:
            self.assertEqual(self.run_game(server, against="12"), 1)
        self.assertTrue(any("already playing" in m for m in logs.output))
        self.assertTrue(any("Could not find game" in m for m in logs.output))
        self.assertEqual(server.actions(), ["login", "myGames", "join"])


if __name__ == "__main__":
    unittest.main()
