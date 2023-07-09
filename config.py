
# Game settings, may affect simulation time
NUMBER_OF_DECKS = 1
NUMBER_OF_PLAYERS = 2
NUMBER_OF_INITIAL_CARDS = 20

SUBDIVIDE_SIMULATIONS = False # to be implemented
TOTAL_SIMULATIONS = 1  # type 0 to make it endless

# This can speed up the simulation by a lot !  1.5 to 2.5 faster if set to True
# It will affect the quality of the data
ONLY_ONE_PLAYER_CAN_WIN = False


## Logging
## This section will mostly have an impact on the generation/saving of logs
ENABLE_LOGGING = True

# Limit the amount of turns per simulation. May increase simulation speed, but lowers the amount of data that can be logged
ENABLE_MAX_TURNS = False
MAX_TURNS = 100

# Automatically filter out games that have no winners
ONLY_LOG_WINNING_GAMES = True

# debug
PLAYER_ID = 900

