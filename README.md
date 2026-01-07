# AEI Readme

This package provides a specification for the Arimaa Engine Interface (AEI).
It also includes some tools for using engines that implement AEI. Including an
interface to the arimaa.com gameroom. A full description of AEI can be found in
the file `AEI_PROTOCOL.md`.

The scripts included for working with an AEI engine are:

- `analyze` - A simple script that runs an engine and has it search a given position or move sequence.
- `gameroom` - AEI controller that connects to the arimaa.com gameroom and plays a game.
- `postal_controller` - Keeps a bot making moves as needed in any postal games it is a participant in.
- `pyrimaa_tests` - Test runner utility.
- `roundrobin` - Plays engines against each other in a round robin tournament.
- `simple_engine` - Very basic AEI engine, just plays random step moves.

Basic examples of using the scripts can be found in the file `USAGE.md`.

The pyrimaa package also includes modules implementing the controller side of
the AEI protocol (`aei.py`), the Arimaa position representation (as bitboards
in `board.py`), and a few utility functions for handling Arimaa timecontrols
(`util.py`).

## Installation

### For CLI Tools (Recommended)

If you just want to use the command-line tools, install with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install aei
```

This creates an isolated environment for the AEI tools and makes them available in your PATH automatically. You can immediately run commands like `analyze`, `gameroom`, `roundrobin`, etc. without managing virtual environments.

### For Library Usage or Traditional Installation

If you need to import `pyrimaa` modules in your own Python code (for example, to use `pyrimaa.aei`, `pyrimaa.board`, or `pyrimaa.util`), use:

```bash
uv pip install aei
```

Or install from a source directory checkout:

```bash
uv pip install .
```

Or skipping `uv` and using plain `pip`:

```bash
pip install aei
```

### For Development

If you're contributing to the AEI project, install in editable mode:

```bash
uv pip install -e .
```

Or with pip:

```bash
pip install -e .
```

