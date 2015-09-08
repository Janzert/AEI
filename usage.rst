===================
Usage documentation
===================

analyze
_______

A simple script that runs an engine and has it search a given position or
move sequence. As an example use it with simple_engine.py that just makes a
random moves::

    cp analyze_example.cfg analyze.cfg
    analyze example_position.txt

If you replace the simple_engine.py with your own bot that implements AEI you
can point your bot at any position.

roundrobin
__________

Plays engines against each other in a round robin tournament.  This is a very
handy way to test your bot against other bots.

The example_roundrobin.cfg contains a config for playing simple_engine against
itself.  It is a good idea to try doing this first to make sure the AEI
tournament is working properly before you put your own bot in there.

First you'll need to make a copy of the example cfg file::

    cp roundrobin_example.cfg roundrobin.cfg

To run the tournament you start it from the commandline::

    roundrobin

Example of the output::

    Number of rounds:  100
    At timecontrol 3s/30s/100/60s/10m
    Giving these settings to all bots:
    hash: 50
    27s
     +-----------------+
    8| . . r r R . . . |
    7| r . . . . . . . |
    6| . . x . . x h . |
    5| H . . . . . . . |
    4| . . h H . R R r |
    3| R D x . . x . . |
    2| . C . . R . . . |
    1| . R . . . D . M |
     +-----------------+
       a b c d e f g h
    Random beat Randomer because of g playing side g
    After round 1 and 0s:
    Random has 1 wins and 0 timeouts
        1 by g
    Randomer has 0 wins and 0 timeouts

    ...

    66g
     +-----------------+
    8| . . . C . . . . |
    7| . . . . . . . . |
    6| R . x . . x . R |
    5| . H . . . . . . |
    4| . . . . . . . . |
    3| . . x . . x . . |
    2| . . . . . . . . |
    1| . . . . d . . . |
     +-----------------+
       a b c d e f g h
    Randomer beat Random because of e playing side g
    After round 100 and 2m22s:
    Random has 59 wins and 0 timeouts
        4 by e
        5 by m
        50 by g
    Randomer has 41 wins and 0 timeouts
        5 by m
        8 by e
        28 by g

The example tournament only has two bot players.  To add additional players
add a new section and add the commandline to execute the player (this should be
an executable that responds to the AEI protocol), e.g.

::

    [MyBot]
    cmdline = ./my_bot

And to add the bot to the tournament modify the bots property::

    bots = random randomer MyBot

or simply replacing one with your own::

    bots = random MyBot

getMove and Older Bots
______________________

Older bots still implement the getMove interface for Arimaa.  To use these bots
with an AEI controller you can use the ``adapt.py`` adapter script written by
Greg Clark and available as part of his `Arimaa client
<https://bitbucket.org/Rabbits/arimaa-client>`_.  Place the executable for the
bot and `adapt.py` in the AEI directory and configure the bot. For example if
you download bot_fairy from `arimaa.com <http://arimaa.com/arimaa/download/>`_
you can add it to ``roundrobin.cfg`` like this::

    [Fairy]
    cmdline = python adapt.py . Fairy

Don't forget to also modify the bots property to add it to the list of bots
that take part in the tournament.

gameroom
________

AEI controller that connects to the arimaa.com gameroom and plays a game.

Similiar to roundrobin or analyze above you'll need to first setup
a ``gameroom.cfg`` file with the bot configuration and gameroom login
information.

Then starting a new game is as simple as::

    gameroom [side]

The first usage starts a single game and waits for an opponent, after which
it plays a full game with that opponent. <side> indicates the side to play
and should be either 'g' for Gold or 's' for Silver, or if not specified,
then it is s. (w or b will also work but may be removed in the future)

To join an existing game use::

    gameroom play|move <opponent name or game number> [side]

This starts an engine then plays a game or move on the server as
specified by the command line arguments. Configuration is provided in the file
``gameroom.cfg``.

The second usage joins a game and either plays a full game or just one move.
'play' indicates the full game should be played. 'move' will play only one
move at most then exit, if it is the opponent's move the interface will exit
immediately. This is handy for postal games. As in the first usage, <side>
optionally indicates which side to play.

postal_controller
_________________

Monitors and directs a bot to play in all of its postal games.

Regular usage just involves setting up a ``gameroom.cfg`` file with the
desired bot settings and simply running::

    postal_controller

If needed you can create a [postal] section in ``gameroom.cfg`` with log
settings or specific bot sections to use in certain games, see the
``gameroom_example.cfg`` file for details.

To cleanly exit the controller after the current move is played create a file
called ``stop_postal`` in the directory ``postal_controller`` was run from.
