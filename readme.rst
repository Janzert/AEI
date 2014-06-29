==========
AEI Readme
==========

This package provides a specification for the Arimaa Engine Interface (AEI).
It also includes some tools for using engines that implement AEI. Including an
interface to the arimaa.com gameroom. A full description of AEI can be found in
the file ``aei-protocol.txt``.

The link used for communication is not specified by the AEI protocol. This
implementation uses either stdio or a socket for the communication. Stdio is
the preferred method for general operation, but in certain programming
languages or environments it may be easier to use socket communication.

When using a socket the controller will listen on an ip and port given to the
engine by adding "--server <dotted quad ip>" and "--port <port number>" options
to its command line. The engine should connect to the specified address and
expect the AEI protocol identifier from the controller.

The scripts included to work with an AEI engine are:

``analyze.py``
  A simple script that runs an engine and has it search a given position or
  move sequence.
``gameroom.py``
  AEI controller that connects to the arimaa.com gameroom and plays a game.
``roundrobin.py``
  Plays engines against each other in a round robin tournament.

There are also a few helper modules located in the python pyrimaa package:

``aei.py``
  Implementation of the controller side of the AEI protocol
``board.py``
  Implements an Arimaa board, step and move generator and some
  related utility functions.

