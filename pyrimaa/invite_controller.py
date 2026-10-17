#!/usr/bin/env python
"""Accept arimaa.com gameroom invitations for a bot and play them.

Usage: invite_controller.py [-c CONFIG] [-b BOT]

Logs the bot's account in to the gameroom lobby the way the web client
does and asks the lobby for its state every 20 to 30 seconds. That keeps
the bot listed as online (clients such as Howdah offer to invite only
players who are), and shows the invitations sent to it. Invitations whose
time control and rated setting are allowed in the [invites] section of the
config are accepted, and each accepted game is played by running
'gameroom play <game id> <side>' with the same config; the rest are
declined with a reason. See gameroom_example.cfg for the settings.

"""

import http.cookiejar
import json
import logging
import optparse
import os
import random
import re
import subprocess
import sys
import time
from configparser import ConfigParser, NoOptionError, NoSectionError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, build_opener
from urllib.request import Request as URLRequest

log = logging.getLogger("invites")

USER_AGENT = "AEI invite_controller (Arimaa bot)"
TIMEOUT = 30


class LobbyError(Exception):
    pass


class _NoRedirect(HTTPRedirectHandler):
    # The login answers with a redirect that sets the session cookie.
    def redirect_request(self, *args, **kwargs):
        return None


def _page_text(page):
    """The text of an HTML page, shortened, for a log line."""
    text = re.sub(r"<[^>]*>", " ", page)
    return " ".join(text.split())[:200]


class Lobby:
    """A login to the gameroom lobby, made as the web client makes it."""

    def __init__(self, url):
        self.base = url.rstrip("/") + "/"
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies), _NoRedirect)
        self.sid = None

    def _request(self, url, form=None, json_body=None):
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
        elif form is not None:
            data = urlencode(form).encode("utf-8")
        else:
            data = None
        # The gameroom answers 404 unless the Referer is a gameroom page.
        req = URLRequest(
            url,
            data,
            headers={
                "Referer": url.split("?")[0],
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with self.opener.open(req, timeout=TIMEOUT) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except HTTPError as err:
            body = err.read().decode("utf-8", "replace")
            if err.code in (301, 302, 303):
                return err.code, body
            if err.code == 404:
                raise LobbyError(
                    f"the server refused {url.split('?')[0]} (404)"
                ) from None
            raise LobbyError(f"HTTP {err.code} from {url.split('?')[0]}") from None
        except (URLError, OSError) as err:
            raise LobbyError(f"network error: {err}") from err

    def login(self, username, password):
        self.cookies.clear()
        self.sid = None
        status, page = self._request(
            self.base + "login.cgi",
            form={"email": username, "password": password, "timezone": "0"},
        )
        for cookie in self.cookies:
            if cookie.name == "sid":
                self.sid = cookie.value
        if self.sid is None:
            raise LobbyError(f"login refused: {_page_text(page)}")
        log.info("Logged in to the lobby as %s", username)

    def state(self):
        """The lobby's state (ASIP 2.0 'state'), as the web lobby polls it."""
        status, body = self._request(
            self.base + "client2gr.cgi",
            json_body={"action": "state", "sid": self.sid},
        )
        try:
            reply = json.loads(body)
        except ValueError:
            raise LobbyError(f"bad state reply: {body[:200]!r}") from None
        if not isinstance(reply, dict):
            raise LobbyError("bad state reply")
        if "error" in reply:
            raise LobbyError(f"state: {reply['error']}")
        return reply

    def accept(self, inviter_id, created):
        # A script gets a redirect (the browser an "accepted" page); the
        # game then shows in the state's mygames.
        url = f"{self.base}acceptInvite.cgi?id={inviter_id}&ts={created}"
        status, page = self._request(url)
        if status not in (301, 302, 303) and "accepted" not in page.lower():
            raise LobbyError(f"accept failed: {_page_text(page)}")

    def decline(self, inviter_id, created, reason):
        status, page = self._request(
            self.base + "declineInvite.cgi",
            form={"reason": reason, "id": inviter_id, "ts": created},
        )
        if status not in (301, 302, 303) and "declined" not in page.lower():
            raise LobbyError(f"decline failed: {_page_text(page)}")

    def set_invites(self, on):
        """Turns the account's invitation flag on or off.

        This is the form on the lobby's 'Invite Me Status' page; a GET of
        the page only shows it. The flag is the account's, kept across
        logins, and shows as 'inviteme' in the state's online list.
        """
        field = "yesinvite" if on else "noinvite"
        status, page = self._request(self.base + "inviteMe.cgi", form={field: "Update"})
        text = " ".join(_page_text(page).lower().split())
        expected = "currently seeking" if on else "currently not seeking"
        if expected not in text:
            raise LobbyError(f"setting invitations failed: {_page_text(page)}")


def entries(state, key):
    """A list from the state reply, which may come as a list or an object."""
    value = state.get(key) or []
    if isinstance(value, dict):
        value = list(value.values())
    return [v for v in value if isinstance(v, dict)]


def invites_on(state, username):
    """Whether the user's invitation flag is on, from the state's online
    list, or None if they aren't listed.

    The lobby treats inviteme as a number ("1", "1 ", or "" when off).
    """
    me = state.get("me")
    my_id = str(me.get("id", "")) if isinstance(me, dict) else ""
    for player in entries(state, "online"):
        if (my_id and str(player.get("id", "")) == my_id) or str(
            player.get("username", "")
        ).lower() == username.lower():
            try:
                return float(str(player.get("inviteme", "")).strip() or 0) > 0
            except ValueError:
                return False
    return None


def normalize_tc(tc):
    return "".join(str(tc).split()).lower()


class Policy:
    """Which invitations to accept, for one bot.

    Each setting comes from the bot's [<bot section>.invites] section if
    it has it there, else from [invites].
    """

    def __init__(self, config, bot_section):
        sections = [f"{bot_section}.invites", "invites"]

        def get(option, default):
            for section in sections:
                if config.has_option(section, option):
                    return config.get(section, option)
            return default

        tcs = re.split(r"[,\n]", get("timecontrols", ""))
        self.timecontrols = [normalize_tc(tc) for tc in tcs if tc.strip()]
        self.rated = get("rated", "unrated").strip().lower()
        if self.rated not in ("rated", "unrated", "both"):
            raise ValueError(
                f"invites: rated must be rated, unrated or both, not {self.rated!r}"
            )
        self.max_games = int(get("max_games", "1"))
        self.poll_interval = max(20, min(30, int(get("poll_interval", "25"))))

    def refusal(self, invitation):
        """Why the invitation can't be accepted, or None if it can."""
        tc = normalize_tc(invitation.get("timecontrol", ""))
        if tc not in self.timecontrols:
            return f"I only play at {', '.join(self.timecontrols)}."
        rated = str(invitation.get("rated", "0")) == "1"
        if rated and self.rated == "unrated":
            return "I only play unrated games."
        if not rated and self.rated == "rated":
            return "I only play rated games."
        return None


class Controller:
    def __init__(self, config, config_path, bot_section, username, password):
        self.config = config
        self.config_path = config_path
        self.bot_section = bot_section
        self.username = username
        self.password = password
        self.policy = Policy(
            config, bot_section or config.get("global", "default_engine")
        )
        self.lobby = Lobby(config.get("global", "gameroom_url"))
        self.games = {}  # gid -> Popen
        self.handled = set()  # (inviter id, createdts)
        self.accepted = {}  # createdts -> (inviter username, time accepted)
        # The invitation flag as first seen, restored on exit, and as of
        # the latest state or change.
        self.invites_found = None
        self.invites_now = None

    def reap(self):
        for gid, proc in list(self.games.items()):
            if proc.poll() is not None:
                log.info("Game %s finished (exit %s)", gid, proc.returncode)
                del self.games[gid]

    def launch(self, gid, side):
        args = [sys.executable, "-m", "pyrimaa.gameroom", "-c", self.config_path]
        if self.bot_section:
            args += ["-b", self.bot_section]
        args += ["play", gid, side]
        log.info("Starting gameroom for game %s as %s", gid, side)
        self.games[gid] = subprocess.Popen(args)

    def start_accepted(self, state):
        """Starts a player for each accepted game that appears in mygames.

        The game made from an invitation has the invitation's createdts.
        """
        for game in entries(state, "mygames"):
            created = str(game.get("createdts", ""))
            gid = str(game.get("id", ""))
            if created not in self.accepted or not gid or gid in self.games:
                continue
            del self.accepted[created]
            if str(game.get("wusername", "")).lower() == self.username.lower():
                side = "w"
            else:
                side = "b"
            self.launch(gid, side)
        for created, (inviter, when) in list(self.accepted.items()):
            if time.time() - when > 300:
                log.warning(
                    "Accepted game against %s never appeared; giving up", inviter
                )
                del self.accepted[created]

    def answer(self, state):
        for inv in entries(state, "invitedmegames"):
            inviter_id = str(inv.get("invitor", ""))
            created = str(inv.get("createdts", ""))
            key = (inviter_id, created)
            if key in self.handled or not inviter_id or not created:
                continue
            self.handled.add(key)
            opponent = inv.get("opponent") or {}
            inviter = opponent.get("username", inviter_id)
            tc = inv.get("timecontrol", "")
            rated = "rated" if str(inv.get("rated", "0")) == "1" else "unrated"
            reason = self.policy.refusal(inv)
            if (
                reason is None
                and len(self.games) + len(self.accepted) >= self.policy.max_games
            ):
                reason = "I'm playing all the games I can; please try again later."
            if reason:
                log.info(
                    "Declining %s's invitation (%s, %s): %s", inviter, tc, rated, reason
                )
                self.lobby.decline(inviter_id, created, reason)
                continue
            log.info("Accepting %s's invitation (%s, %s)", inviter, tc, rated)
            self.lobby.accept(inviter_id, created)
            self.accepted[created] = (inviter, time.time())

    def slots_free(self):
        return len(self.games) + len(self.accepted) < self.policy.max_games

    def update_invites(self, state):
        """Turns the invitation flag off while every game slot is taken and
        on while one is free, sending a change only when it's needed."""
        found = invites_on(state, self.username)
        if found is None:
            return
        if self.invites_found is None:
            self.invites_found = found
        self.invites_now = found
        wanted = self.slots_free()
        if wanted != found:
            log.info("Turning invitations %s", "on" if wanted else "off")
            self.lobby.set_invites(wanted)
            self.invites_now = wanted

    def restore_invites(self):
        """Leaves the invitation flag as it was found."""
        if self.invites_found is None or self.invites_now == self.invites_found:
            return
        try:
            if self.lobby.sid is None:
                self.lobby.login(self.username, self.password)
            log.info(
                "Turning invitations %s again", "on" if self.invites_found else "off"
            )
            self.lobby.set_invites(self.invites_found)
            self.invites_now = self.invites_found
        except LobbyError as exc:
            log.warning("Could not restore the invitation setting: %s", exc)

    def run(self):
        failures = 0
        while True:
            if os.path.exists("stop_invites"):
                log.info("Exiting after finding the stop file 'stop_invites'")
                self.restore_invites()
                return 0
            try:
                if self.lobby.sid is None:
                    self.lobby.login(self.username, self.password)
                state = self.lobby.state()
                self.reap()
                self.answer(state)
                if self.accepted:
                    # The game is made when the invitation is accepted.
                    time.sleep(3)
                    state = self.lobby.state()
                    self.start_accepted(state)
                self.update_invites(state)
                failures = 0
            except LobbyError as exc:
                failures += 1
                log.warning("Lobby request failed (%d in a row): %s", failures, exc)
                # The login may have expired or been ended; log in again.
                self.lobby.sid = None
                if failures >= 3:
                    time.sleep(min(600, 30 * 2 ** (failures - 3)))
            time.sleep(self.policy.poll_interval + random.uniform(-2, 2))


def main(args=sys.argv):
    opt_parser = optparse.OptionParser(
        usage="usage: %prog [-c CONFIG] [-b BOT]",
        description="Accept gameroom invitations for a bot and play them.",
    )
    opt_parser.add_option(
        "-c", "--config", default="gameroom.cfg", help="Configuration file to use."
    )
    opt_parser.add_option("-b", "--bot", help="Bot section to use.")
    options, args = opt_parser.parse_args(args)
    if len(args) > 1:
        print(f"Unrecognized command line arguments: {args[1:]}")
        return 1
    config = ConfigParser()
    if not config.read(options.config):
        print(f"Could not open '{options.config}'.")
        return 1

    logfmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    try:
        log_dir = config.get("Logging", "directory")
    except (NoOptionError, NoSectionError):
        log_dir = "."
    os.makedirs(log_dir, exist_ok=True)
    loghandler = logging.FileHandler(
        os.path.join(log_dir, "invites-" + time.strftime("%Y-%m") + ".log")
    )
    loghandler.setFormatter(logfmt)
    log.addHandler(loghandler)
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(logfmt)
    log.addHandler(consolehandler)
    log.setLevel(logging.INFO)
    log.propagate = False

    bot_section = options.bot or config.get("global", "default_engine")
    try:
        username = config.get(bot_section, "username")
        password = config.get(bot_section, "password")
    except (NoOptionError, NoSectionError):
        try:
            username = config.get("global", "username")
            password = config.get("global", "password")
        except NoOptionError:
            log.error("Could not find username/password in config.")
            return 1

    try:
        controller = Controller(config, options.config, options.bot, username, password)
    except ValueError as exc:
        print(exc)
        return 1
    if not controller.policy.timecontrols:
        print(
            f"No time controls to accept: set timecontrols in [{bot_section}.invites]"
            " or [invites]."
        )
        return 1
    try:
        return controller.run()
    except KeyboardInterrupt:
        log.info("Stopped; games already started keep playing.")
        controller.restore_invites()
        return 0


if __name__ == "__main__":
    sys.exit(main())
