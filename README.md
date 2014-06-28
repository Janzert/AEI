# AEI

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

The scripts included to work with an AEI engine are: analyze.py, roundrobin.py
and gameroom.py

## analyze.py

A simple script that runs an engine and has it search a given position or
move sequence. As an example use it with simple_engine.py that makes random
moves:

```bash
cp analyze_example.cfg analyze.cfg
./analyze example_position.atp
```

If you replace the simple_engine.py with your own bot that implements AEI you
can point any position at your bot.

## roundrobin.py

Plays engines against each other in a round robin tournament.  This is a very
handy way to test your bot against other bots.

The example_roundrobin.cfg contains config for matching bot_opfor against the
simple_engine.py that makes random moves.  It is a good idea to try doing this
first to make sure the AEI tournament is working properly before you put your
own bot in there.

First you'll need to make a copy of the example cfg file:

```bash
cp roundrobin_example.cfg roundrobin.cfg
```

Before you can run the example round robin tournament on your computer you'll
first have to download bot_opfor from [here](http://arimaa.janzert.com/opfor/).
Place the executable where it AEI can find (you may need to modify the
  rounrobin.cfg file, and point it to the right place)

To run the tournament you start it from the commandline:

```bash
./roundrobin.py
```
Example of the output:

```
Number of rounds:  10
At timecontrol 20s/20s/100/60s/45m
Giving these settings to all bots:
hash: 50
12s
 +-----------------+
8| r R . r m r r . |
7| . . r r h . . d |
6| H . x . . x c r |
5| d . . R . . . . |
4| . . . R M . . . |
3| . . x . . x D . |
2| . D C . E C . H |
1| . . R . R R R R |
 +-----------------+
   a b c d e f g h  
OpFor wins because of g playing side g
After round 1 and 1m13s:
OpFor has 1 wins and 0 timeouts
    1 by g
Random has 0 wins and 0 timeouts
```

The example tournament only has two bot players.  To add additional players
add a new section and add the commandline to execute the player (this should be
  an executable that responds to the AEI protocol), e.g.

```
[MyBot]
cmdline = ./my_bot
```

And to add the bot to the tournament modify the bots property:

```
bots = OpFor Random MyBot
```

### getMove and Older Bots

Older bots still implement the getMove interface for Arimaa.  To use these bots
in an AEI tournament you can use the adapt.py adapter script.  Place the
executable for the bot in the AEI directory and configure the bot, for example
if you download bot_fairy from [here](http://arimaa.com/arimaa/download/) you
can add it to the tournament like this:

```
[Fairy]
cmdline = python adapt.py . Fairy
```

Don't forget to modify the bots property to add it to the list of bots that take
part in the tournament.

## gameroom.py

AEI controller that connects to the arimaa.com gameroom and plays a game.

## Helper Modules

There are also a few helper modules located in the python pyrimaa package:

### aei.py

Implementation of the controller side of the AEI protocol

### board.py

Implements an Arimaa board, step and move generator and some related utility
functions.
