#!/usr/bin/env python

import logging
import optparse
import os.path
import sys
import time
from configparser import ConfigParser, NoOptionError
from configparser import Error as ConfigError

from pyrimaa import gameroom

log = logging.getLogger("postal")


def main(args=sys.argv):
    opt_parser = optparse.OptionParser(
        usage="usage: %prog [-c CONFIG] [-b BOT]",
        description="Manage bot playing multiple postal games.",
    )
    opt_parser.add_option(
        "-c", "--config", default="gameroom.cfg", help="Configuration file to use."
    )
    opt_parser.add_option("-b", "--bot", help="Bot section to use as the default.")
    options, args = opt_parser.parse_args(args)
    if len(args) > 1:
        print(f"Unrecognized command line arguments: {args[1:]}")
        return 1
    config = ConfigParser()
    read_files = config.read(options.config)
    if len(read_files) == 0:
        print(f"Could not open '{options.config}'.")
        return 1

    try:
        log_dir = config.get("postal", "log_dir")
    except ConfigError:
        try:
            log_dir = config.get("Logging", "directory")
        except ConfigError:
            log_dir = "."
    if not os.path.exists(log_dir):
        print(f"Log directory '{log_dir}' not found, attempting to create it.")
        os.makedirs(log_dir)

    try:
        log_filename = config.get("postal", "log_file")
    except ConfigError:
        log_filename = "postal-" + time.strftime("%Y-%m") + ".log"
    log_path = os.path.join(log_dir, log_filename)
    logfmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    loghandler = logging.FileHandler(log_path)
    loghandler.setFormatter(logfmt)
    log.addHandler(loghandler)
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(logfmt)
    log.addHandler(consolehandler)
    log.propagate = False
    gameroom.init_logging(config)

    gameroom_url = config.get("global", "gameroom_url")
    if options.bot:
        bot_section = options.bot
    else:
        bot_section = config.get("global", "default_engine")
    try:
        bot_username = config.get(bot_section, "username")
        bot_password = config.get(bot_section, "password")
    except ConfigError:
        try:
            bot_username = config.get("global", "username")
            bot_password = config.get("global", "password")
        except NoOptionError:
            log.error("Could not find username/password in config.")
            return 1

    while True:
        try:
            open("stop_postal")
            log.info("Exiting after finding stop file")
            return 0
        except OSError:
            pass
        gr_con = gameroom.GameRoom(gameroom_url)
        gr_con.login(bot_username, bot_password)
        games = gr_con.mygames()
        gr_con.logout()
        total_games = len(games)
        games = [g for g in games if g["postal"] == "1"]
        postal_games = len(games)
        games = [g for g in games if g["turn"] == g["side"]]
        my_turn_games = len(games)
        log.info(
            f"Found {total_games} games {postal_games} with  postal games "
            f"and {my_turn_games} on my turn."
        )
        if games:
            games.sort(key=lambda x: x["turnts"])
            for game_num, game in enumerate(games):
                try:
                    open("stop_postal")
                    log.info("Exiting after finding stop file")
                    return 0
                except OSError:
                    pass
                log.info(
                    f"{game_num + 1}/{my_turn_games}: Playing move against "
                    f"{game['player']} game #{game['gid']}"
                )
                game_args = ["gameroom", "move", game["gid"], game["side"]]
                if config.has_option("postal", game["gid"]):
                    section = config.get("postal", game["gid"])
                    game_args += ["-b", section]
                    log.info(f"Using section {section} for use with gid #{game['gid']}")
                elif config.has_option("postal", game["player"]):
                    section = config.get("postal", game["player"])
                    game_args += ["-b", section]
                    log.info(
                        f"Using section {section} for use against {game['player']}"
                    )
                gmoptions = gameroom.parseargs(game_args)
                res = gameroom.run_game(gmoptions, config)
                if res is not None and res != 0:
                    log.warning(f"Error result from gameroom run {res}.")
        else:
            log.info("No postal games with a turn found, sleeping.")
            time.sleep(300)

    return 0


if __name__ == "__main__":
    sys.exit(main())
