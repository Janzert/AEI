==========
AEI Readme
==========

This package provides a specification for the Arimaa Engine Interface (AEI).
It also includes some tools for using engines that implement AEI. Including an
interface to the arimaa.com gameroom. A full description of AEI can be found in
the file ``aei-protocol.txt``.

The scripts included to work with an AEI engine are:

``analyse.py``
  A simple script that runs an engine and has it searching on a given position
``gameroom.py``
  AEI controller that connects to the arimaa.com gameroom and plays a game.
``match.py``
  Plays two engines against each other.

There are also a few helper modules:

``aei.py``
  Implementation of the controller side of the AEI protocol
``board.py``
  Implements an Arimaa board, step and move generator and some
  related utility functions.

