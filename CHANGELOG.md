# Changelog

All notable changes to AEI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries before 1.4.1 were reconstructed from the release notes and commit
history.

## [Unreleased]

### Added

- GitHub Actions workflows: CI runs the tests on Python 3.8 to 3.14 (plus
  Windows and macOS), ruff, and package checks on every push and pull
  request; publishing a GitHub release builds the package, attaches it to
  the release and uploads it to PyPI with trusted publishing.

### Fixed

- aei: a socket engine failed to start on macOS when port 40015 was in
  use, instead of trying the next port, because only the Linux and Windows
  "address in use" error numbers were recognized.

## [1.4.1] - 2026-10-02

### Fixed

- gameroom: arimaa.com now rejects gameroom requests (with a 404) unless
  they carry a Referer from a gameroom page, which stopped `gameroom` from
  logging in. Every request now sends one.
- gameroom: a refused login (such as a wrong password) is reported with the
  server's message and exits with status 1, instead of crashing with
  `KeyError: 'sid'`.
- gameroom: an HTTP error from the gameroom is logged with a clear message,
  and one received while logging in or joining a game exits with status 1
  instead of a traceback.
- gameroom: joining a game that another running `gameroom` process is
  already playing crashed with a `TypeError` instead of skipping it. The
  "already playing" message is now logged only when that is true.
- gameroom: a Windows connection timeout during address lookup is retried
  again, and other lookup failures raise the network error rather than a
  `TypeError`.
- The source distribution now includes the Markdown documentation
  (`USAGE.md`, `AEI_PROTOCOL.md`, `CHANGELOG.md`).

### Changed

- roundrobin: elapsed times are printed in whole seconds.
- Development: the `dev` extra installs pre-commit only on Python 3.10 and
  newer, and `uv.lock` now pins virtualenv 21.14.4 and filelock 4.0.9,
  which fix the advisories Dependabot reported. Neither is a dependency of
  AEI itself.

### Added

- Tests for the gameroom interface.
- This changelog.

## [1.4] - 2026-01-08

A minor release to bring the Python code and packaging up to date.

### Changed

- Python 2 support is dropped; Python 3.8 is now the minimum.
- Packaging moved from `setup.py` to `pyproject.toml` (PEP 621). The uv
  package manager is supported, with a lock file, and `uv tool install` is
  the recommended way to install the command-line tools.
- Documentation (README, USAGE, AEI_PROTOCOL) converted from
  reStructuredText to Markdown, with clearer installation instructions for
  tool, library and development use.
- Code modernized: f-strings throughout, current threading and subprocess
  APIs, and Python 2 compatibility code removed.
- Added ruff linting and formatting, pre-commit hooks, and optional coverage
  reporting (terminal, HTML and XML) in the test runner.

### Removed

- The slower x88 board implementation.

### Fixed

- Bare `except:` clauses that could catch system-exiting exceptions.
- A mutable default argument and a `.lstrip()` misuse in the tests, and
  numerous lint issues.

## [1.3] - 2021-06-07

### Added

- Python 3 support, keeping Python 2.7 compatibility. Thanks to TFiFiE for
  the initial Python 3 work.
- Games can be lost by playing an illegal move (Gregory Clark).
- Tests for the aei, analyze, board, game and simple_engine modules.

### Fixed

- Several minor bugs, many found while writing the new tests, including
  `parse_long_pos` and random step move generation in the board module.
- gameroom handles an `OSError` from the server connection.
- roundrobin config error handling, and running the tests on Windows.

## [1.2] - 2015-09-09

Few protocol changes, but a much more robust implementation.

### Added

- Repetition rule checking and resignation in the game module.
- gameroom: config file and bot section selectable on the command line,
  login details settable globally in `gameroom.cfg`, and an option to send
  network logging to a separate file.
- postal_controller: per-game bot sections and usage documentation.
- analyze: strict legality checking is configurable (original patch by
  JDB), plus short option names.
- roundrobin: per-bot time controls, `min_time_left`, and 2008cc support.
- Better usage documentation (thanks to Leon Messerschmidt and
  lightvector), and pip install instructions.
- Tests are included in the built packages.

### Changed

- The scripts moved into the `pyrimaa` package, with setuptools entry
  points.
- postal_controller calls the gameroom interface directly instead of
  running a subprocess.
- analyze and roundrobin option and config handling reworked.

### Fixed

- Reserve time handling for time controls without 100% reserve
  replacement (thanks to Hippo).
- The gameroom interface is more resistant to network problems and game
  timeouts, and sets an error exit status where it used to exit normally.
- Removing silver pieces in the board module, and a check for too many
  steps in a move.
- Engines are killed more reliably on Windows.

## [1.1] - 2010-07-18

### Added

- roundrobin: Bayeselo-compatible PGN output (thanks to Jeff Bacher), more
  game information in the PGN file, game length reporting, and game time
  and move limits.

### Changed

- Engine processes are started through the shell, so engine command lines
  are parsed as usual.
- Moves parsed from strings are fully checked for legality by default.

### Fixed

- Wins at the game time limit are assigned by the current rules.
- `check_step()` and `piece_at()` in the board module (fixes by Rabbits).
- roundrobin no longer crashes when no time control is given.

## [1.0] - 2010-01-26

### Added

- analyze: an option to not search the position, and engine options sent
  after the position.
- roundrobin: configurable communication method and logging, and the time
  spent reported after each round.
- gameroom: retries when fetching the permanent game id after a game, and
  the side can be given as g/w on the command line.
- Examples in the AEI protocol document.

### Fixed

- roundrobin works with engines older than AEI version 1 again, and
  handles time controls with an unlimited maximum reserve.
- analyze errors with move lists and missing file names.

## 1.0beta1 - 2009-11-02

First tagged release.

[Unreleased]: https://github.com/Janzert/AEI/compare/1.4.1...HEAD
[1.4.1]: https://github.com/Janzert/AEI/compare/1.4...1.4.1
[1.4]: https://github.com/Janzert/AEI/compare/1.3...1.4
[1.3]: https://github.com/Janzert/AEI/compare/1.2...1.3
[1.2]: https://github.com/Janzert/AEI/compare/1.1...1.2
[1.1]: https://github.com/Janzert/AEI/compare/1.0...1.1
[1.0]: https://github.com/Janzert/AEI/compare/1.0beta1...1.0
