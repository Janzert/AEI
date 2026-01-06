# AEI Readme

This package provides a specification for the Arimaa Engine Interface (AEI).
It also includes some tools for using engines that implement AEI. Including an
interface to the arimaa.com gameroom. A full description of AEI can be found in
the file `AEI_PROTOCOL.md`.

The scripts included for working with an AEI engine are:

- `analyze` - A simple script that runs an engine and has it search a given position or move sequence.
- `gameroom` - AEI controller that connects to the arimaa.com gameroom and plays a game.
- `postal_controller` - Keeps a bot making moves as needed in any postal games it is a participant in.
- `roundrobin` - Plays engines against each other in a round robin tournament.
- `simple_engine` - Very basic AEI engine, just plays random step moves.

Basic examples of using the scripts can be found in the file `USAGE.md`.

The pyrimaa package also includes modules implementing the controller side of
the AEI protocol (`aei.py`), the Arimaa position representation (as bitboards
in `board.py`), and a few utility functions for handling Arimaa timecontrols
(`util.py`).

## Installation

### Using uv (recommended)

If you have [uv](https://docs.astral.sh/uv/) installed, you can install
the latest release with:

```bash
uv pip install aei
```

Or install from the source directory:

```bash
uv pip install .
```

### Using pip

You can also install with pip:

```bash
pip install aei
```

For development, you can install in editable mode:

```bash
uv pip install -e .
# or with pip:
pip install -e .
```
