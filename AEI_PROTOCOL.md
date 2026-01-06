# Arimaa Engine Interface (AEI)

## Introduction

The Arimaa Engine Interface (AEI) is meant to provide a standard protocol of
communication between an Arimaa engine and a controller. An engine is a program
capable of taking the state of an Arimaa game and selecting a legal move to
make. A controller is anything that wants to communicate with and control an
engine. This could be anything from a simple script to have the engine analyse
a single position to a GUI program that allows games to be played with humans
or other engines.

AEI was based off of the Universal Chess Interface protocol and follows much of
its general structure. One of the priorities in designing AEI was ease of
implementation. This led to things like trying to make the parsing as simple as
possible and keeping the raw protocol easily human readable to ease debugging.

AEI does assume a real-time, full duplex, reliable communication channel but
otherwise does not depend on a specific method. The current implementation
works over standard input/output or socket based communication.

AEI also tries to avoid making any assumption or restriction on the internal
workings of an engine. At the same time it tries to provide the facilities to
expose any interesting information to the user. As well as allow complete
control of the engine.

## General Operation

AEI is a text based, asynchronous protocol.

An AEI message (command or response) is given as a single line of text. A line
of text can end with either a line feed (0x0a) or the native line ending for
operating system the program is running under. Controllers that are able to
communicate with engines remotely should therefore correctly handle any of the
common line ending styles. Multiple line ending styles should not be mixed
within a single session.

A message begins with a message type indicator. The type indicator extends to
the first space character in the message. The format of the remainder of the
message varies by message type.

An engine upon receiving an unrecognized message should indicate an error and
exit.

A controller upon receiving an unrecognized message should indicate an error
to the user and may end the session.

If a message is received at an inappropriate time an error should be logged.

An engine should try and process messages as soon as possible even while
thinking.

A session has two phases. The opening phase begins after communication has been
established between the controller and engine with the controller sending the
message "aei" to indicate the start of the session. The engine then replies
with identification messages and ends the opening phase with the "aeiok"
message. This signals the start of the main phase which continues until the
controller sends the "quit" command or the communication channel is closed.

Engines should start up and respond to the initial "aei" message as soon as
possible and delay any lengthy initialisation until after the opening phase is
complete.

Engines should never start thinking until after a "go" command is received.

## Controller to Engine Messages

These are all the messages a controller can send to an engine.

### aei

First message sent to begin the opening phase. Waits for
"protocol-version", "id" messages and an "aeiok" message back from the
engine to end the opening phase.

### isready

Ping engine. Waits for engine to respond with "readyok" to signify that
the engine has finished processing any previous commands.

### newgame

Signals the start of a new game. The game state should include an empty
board with gold to make its initial setup move. The game could continue
with the controller sending a gold setup move (with a makemove command),
the controller instructing the engine to find a gold setup move (with a go
command) or changed to an arbitrary board position (with a setposition
command). Any timecontrol previously set should still be used but reserve
times should be reset to the initial value.

### setposition <side> <position>

Set the current position. Positions are given by the side to move (g/s)
and a board consisting of an opening and closing square bracket ([]) and
a piece letter or a space for each of the 64 squares from left to right
and top to bottom (a8-h8, a7-h7...a1-h1).

### setoption name <id> [value <x>]

Set any engine configuration as well as various game state settings.
For numeric options, except as noted below, 0 means unlimited and is the
default initial value.

If an engine receives an unrecognized option it should log a warning.

The standard game state options are (all times are given in seconds):

- **tcmove** - The per move time for the game.
- **tcreserve** - The starting reserve time.
- **tcpercent** - The percent of unused time added to the reserve. The initial value is 100 percent. 0 means no unused time is added to the reserve.
- **tcmax** - The maximum reserve time.
- **tctotal** - Time limit for the total length of the game.
- **tcturns** - Maximum number of moves the game can last.
- **tcturntime** - Maximum time a single move can last.
- **greserve** - Amount of reserve time for gold.
- **sreserve** - Amount of reserve time for silver.
- **gused** - Amount of time used on gold's last turn.
- **sused** - Amount of time used on silver's last turn.
- **lastmoveused** - Amount of time used on the last turn.
- **moveused** - Amount of time used so far on the current turn.
- **opponent** - Opponent's name.
- **opponent_rating** - Opponent's current rating.
- **rating** - Engine's current rating.
- **rated** - Current game is rated. 1 is rated, 0 is unrated. The default is rated.
- **event** - Event the current game is a part of.

The following options are not required but if an engine does allow setting
the option described it should use the standard option name.

Other standard options:

- **hash** - Size in megabytes of the hash table.
- **depth** - If set to a positive number the depth in steps to search a position. An engine may honor a minimum depth of 4. A value of 0 or less indicates no fixed depth.

### makemove <move>

Make a move. Stop any current search in progress. The move format is
simply the actual steps made, using the official Arimaa notation for
recording games[^1]. The move number and side is not sent.

[^1]: See <http://arimaa.com/arimaa/learn/notation.html> for details.

### go [ponder]

Start searching using the current position and game state. A plain go
command means the engine should send a bestmove according to its own time
management or other options already set (e.g. fixed depth). If given the
subcommand **ponder** the engine should start pondering on the current
position with the expectation that it will later receive the opponents
actual move.

### stop

Stop the current search. The engine should respond with the bestmove found.

### quit

Exit the session. In normal operation the engine should completely end
its program as quickly as possible. The controller may, but is not
required to, process further messages from the engine after sending a
"quit" message. The controller should not send any further messages after
a "quit" message.

## Engine to Controller Messages

### protocol-version 1

Sent as the first response after receiving the initial "aei" protocol
identifier.

### id <type> <value>

Send engine identification during the opening phase of the session. Only
one identifier of each type may be sent.

The list of identifier types are:

- **name**
- **author**
- **version**

### aeiok

End opening phase and start the general phase of the session.

### readyok

Answer to "isready" message after all previous messages from the
controller have been processed.

### bestmove <move>

Best move found in search

### info <type> <value>

Information about the current search. In particular things that a GUI may
want to show to a user separately from a general log. An engine may send
any type, but the following have defined meanings and should not be used
differently:

- **score <n>** - The current score from the engines perspective (i.e. a positive score is in favor of the current side making a move). The score should be in centi-rabbits (i.e. scaled such that an initial rabbit capture is worth 100).
- **depth <n>** - The depth in steps the search has finished. When in the midst of searching the next step a plus sign (+) should be appended. For example when sending immediately after finishing the search to depth 10 but before the depth 11 search is started "info depth 10" could be sent. Once depth 11 is started but not yet finished "info depth 10+" should be sent.
- **nodes <n>** - The number of nodes searched so far in the current search. This should include any nodes in a quiescence search.
- **pv <variation>** - The current primary variation. After the first move, subsequent moves are prefixed by the color to move (e.g. pv Ed2n Ed3n b ee7s ee6s w Ed4n).
- **time <seconds>** - Time in seconds the current search has lasted.
- **currmovenumber <n>** - The number of the root move currently, or just finished, being searched.

### log <string>

Any information the engine wants to log. Log messages may start with
"Error:", "Warning:" or "Debug:" to indicate special handling by the
controller.

## Example Sessions

Below are a couple examples of AEI being used. Lines prefixed with 'CTL:' are
from the controller to the engine and 'ENG:' from the engine to the controller.

Here is a complete session with OpFor doing a short analyses of an opening
position:

```
CTL: aei
ENG: protocol-version 1
ENG: id name OpFor
ENG: id author Janzert
ENG: aeiok
CTL: isready
ENG: log Set transposition table size to 10MB (187245 entries)
ENG: readyok
CTL: setoption name depth value 6
CTL: newgame
ENG: log Search depth set to 6
ENG: log Starting new game.
CTL: setposition g [rrrrrrrrhdcemcdh                                HDCMECDHRRRRRRRR]
CTL: go
ENG: log Starting search
ENG: info depth 4
ENG: info time 0
ENG: info nodes 10066
ENG: info qnodes 3353
ENG: info score 65
ENG: info pv Ee2n Ee3n Ee4n Ee5n
ENG: info depth 5
ENG: info time 0
ENG: info nodes 20159
ENG: info qnodes 6726
ENG: info score 29
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s
ENG: info depth 6
ENG: info time 1
ENG: info nodes 30466
ENG: info qnodes 10236
ENG: info score 18
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s me7w
ENG: log Searched 30466 nodes, 60932.00 nps, 6646 tthits.
ENG: log Finished search in 0.50 seconds, average 0.50, max 0.50.
ENG: bestmove Ee2n Ee3n Ee4n Ee5n
ENG: log Positions allocated 4313, in reserve 4309(1.43MB).
CTL: quit
ENG: log Exiting by server command.
CTL: quit
```

Here is the startup and first few moves in a blitz game:

```
CTL: aei
ENG: protocol-version 1
ENG: id name OpFor
ENG: id author Janzert
ENG: aeiok
ENG: log Set transposition table size to 10MB (187245 entries)
CTL: isready
ENG: readyok
CTL: setoption name hash value 500
CTL: isready
ENG: log Set transposition table size to 500MB (9362285 entries)
ENG: readyok
CTL: setoption name rated value 1
CTL: newgame
CTL: isready
ENG: log Starting new game.
ENG: readyok
CTL: setoption name tcmove value 15
CTL: setoption name tcreserve value 90
CTL: setoption name tcpercent value 100
CTL: setoption name tcmax value 120
CTL: setoption name tctotal value 7200
CTL: setoption name tcturns value 0
CTL: setoption name tcturntime value 0
CTL: isready
ENG: readyok
CTL: setoption name rating value 1857
CTL: setoption name opponent value bot_Clueless2009Blitz
CTL: setoption name opponent_rating value 1918
CTL: setoption name rated value 1
CTL: setoption name moveused value 0
CTL: setoption name greserve value 90
CTL: setoption name sreserve value 90
CTL: go
ENG: log Starting search
ENG: log Min search: 13.50 Max: 94.00
ENG: log Searched 0 nodes, -nan nps, 0 tthits.
ENG: log Finished search in 0.00 seconds, average 0.00, max 0.00.
ENG: bestmove Rh1 Rg1 Rf1 Rc1 Rb1 Ra1 Rh2 Ra2 Ce1 Cf2 Dd1 Dc2 Hg2 Hb2 Md2 Ee2
CTL: makemove Rh1 Rg1 Rf1 Rc1 Rb1 Ra1 Rh2 Ra2 Ce1 Cf2 Dd1 Dc2 Hg2 Hb2 Md2 Ee2
CTL: go ponder
ENG: log Positions allocated 3, in reserve 1(0.00MB).
ENG: log made move Rh1 Rg1 Rf1 Rc1 Rb1 Ra1 Rh2 Ra2 Ce1 Cf2 Dd1 Dc2 Hg2 Hb2 Md2 Ee2
ENG: log Starting search
ENG: log Min search: 13.50 Max: 94.00
ENG: log Searched 0 nodes, -nan nps, 0 tthits.
ENG: log Finished search in 0.00 seconds, average 0.00, max 0.00.
ENG: log Positions allocated 4, in reserve 1(0.00MB).
CTL: makemove ed7 hg7 hb7 me7 de8 dd8 cf7 cc7 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
ENG: log made move ed7 hg7 hb7 me7 de8 dd8 cf7 cc7 ra7 rh7 ra8 rb8 rc8 rf8 rg8 rh8
CTL: setoption name moveused value 0
CTL: setoption name greserve value 90
CTL: setoption name sreserve value 90
CTL: setoption name gused value 0
CTL: setoption name sused value 3
CTL: setoption name lastmoveused value 3
CTL: go
ENG: log Starting search
ENG: log Min search: 13.50 Max: 94.00
ENG: info depth 4
ENG: info time 1
ENG: info nodes 10008
ENG: info qnodes 3333
ENG: info score 66
ENG: info pv Ee2n Ee3n Ee4n Ee5n
CTL: setoption name moveused value 1
ENG: info depth 5
ENG: info time 1
ENG: info nodes 20039
ENG: info qnodes 6685
ENG: info score 37
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s
ENG: info depth 6
ENG: info time 1
ENG: info nodes 30191
ENG: info qnodes 10108
ENG: info score 26
ENG: info pv Ee2n Ee3n Ee4n Ee4n b ed7s me7w
ENG: info depth 7
ENG: info time 1
ENG: info nodes 37106
ENG: info qnodes 12160
ENG: info score 7
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s ed6s hg7s
ENG: info depth 8
ENG: info time 2
ENG: info nodes 51087
ENG: info qnodes 15672
ENG: info score 6
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s ed6s hg7s dd8s
ENG: info depth 9
ENG: info time 2
ENG: info nodes 79019
ENG: info qnodes 22266
ENG: info score 23
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s dd8s rh7s rh6w w Ee6s
ENG: info depth 10
ENG: info time 6
ENG: info nodes 182581
ENG: info qnodes 76480
ENG: info score 29
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s dd8s rh7s rh6w w Ee6s Ee5e
ENG: info depth 11
ENG: info time 12
ENG: info nodes 342008
ENG: info qnodes 158205
ENG: info score 40
ENG: info pv Ee2n Ee3n Ee4n Ee5n b ed7s rh7s rh6w ed6n
ENG: log Min search time reached
ENG: log move_length 15.06, decision_length 14.08, time_left 78.94
ENG: log Searched 470983 nodes, 30758.07 nps, 89239 tthits.
ENG: log Finished search in 15.31 seconds, average 15.31, max 15.31.
ENG: bestmove Ee2n Ee3n Ee4n Ee5n
CTL: makemove Ee2n Ee3n Ee4n Ee5n
CTL: go ponder
ENG: log Positions allocated 4277, in reserve 4271(1.41MB).
ENG: log made move Ee2n Ee3n Ee4n Ee5n
ENG: log Starting search
ENG: log Min search: 13.50 Max: 94.00
CTL: makemove hb7s hg7s ed7s dd8s
CTL: setoption name moveused value 0
CTL: setoption name greserve value 89
CTL: setoption name sreserve value 92
CTL: setoption name gused value 0
CTL: setoption name sused value 13
CTL: setoption name lastmoveused value 13
CTL: go
ENG: log Stopping engine for incoming move.
ENG: log made move hb7s hg7s ed7s dd8s
ENG: log Starting search
ENG: log Min search: 13.45 Max: 93.00
ENG: info depth 4
ENG: info time 1
ENG: info nodes 16711
```

## Acknowledgements

Thanks first to Omar Syed not only for designing a great game but also for all
the effort and expense in giving the community a great place to play. He has
also given valuable feedback for changes and clarifications to the protocol.

As mentioned before the structure of this protocol relies heavily on concepts
from the Universal Chess Interface Protocol. Without it AEI would surely be
much worse off.

Oystein Gjerstad compiled the initial list of message types and descriptions
from my initial implementation.

Arimaa is a registered trademark of Omar Syed. The game of Arimaa is also
patented by Omar Syed. Further information on the game is available at
<http://arimaa.com/>.

## Changes

### Version 1

Added "protocol-version" message so controllers can remain compatible with
old engines.

Change all colors in the protocol to g (gold) and s (silver).
