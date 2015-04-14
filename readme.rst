==========
AEI Readme
==========

This package provides a specification for the Arimaa Engine Interface (AEI).
It also includes some tools for using engines that implement AEI. Including an
interface to the arimaa.com gameroom. A full description of AEI can be found in
the file ``aei-protocol.txt``.

The scripts included for working with an AEI engine are:

``analyze``
  A simple script that runs an engine and has it search a given position or
  move sequence.
``gameroom``
  AEI controller that connects to the arimaa.com gameroom and plays a game.
``postal_controller``
  Keeps a bot making moves as needed in any postal games it is a participant
  in.
``roundrobin``
  Plays engines against each other in a round robin tournament.
``simple_engine``
  Very basic AEI engine, just plays random step moves.

Basic examples of using the scripts can be found in the file ``usage.rst``.

The pyrimaa package also includes modules implementing the controller side of
the AEI protocol (``aei.py``), the Arimaa position representation (as bitboards
in ``board.py`` and x88 in ``x88board.py``), and a few utility functions for
handling Arimaa timecontrols (``util.py``).

The link used for communication is not specified by the AEI protocol. This
implementation uses either stdio or a socket for the communication. Stdio is
the preferred method for general operation, but in certain programming
languages or environments it may be easier to use socket communication.

When using a socket the controller will listen on an ip and port given to the
engine by adding "--server <dotted quad ip>" and "--port <port number>" options
to its command line. The engine should connect to the specified address and
expect the AEI protocol identifier from the controller.
