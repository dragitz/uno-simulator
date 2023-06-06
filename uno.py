# Uno cards game simulator with deep learning.
# Model saving and loading using keras and tensorflow.
# Uses threads to simulate multiple games
# Tested on Windows 10

"""
TrueSkill analysis (100k games):
- Random moves with mu=30 and sigma=8, and multiple people can win, leads to trueskill --> 28 - 38
- Random moves with mu=30 and sigma=8, and only 1 person can win, leads to trueskill --> 25 - 33

TrueSkill analysis (500k games):
- Random moves with mu=30 and sigma=8, and multiple people can win, leads to trueskill --> 24 - 40


"""

"""
    TODO:
        - Implement (efficient) data collection with periodical saving
        - Create deep learning model
        - Compute TR of model
        - Create a pygame interface for playing vs bots
        - Implement TCP to play with friends via LAN (Radmin, Hamachi, ...)
"""

import config

from game_utility import generateDeck, shuffleDeck, drawCards, spawnPlayers, dealCards
from game_logic import skipTurn, canPlayerPlay, playCard, changeColor, canCardBePlayed, logic, update_trueskill
from trueskill import Rating



class Card:
    def __init__(self, color, type, number, draw_amount, changes_color, points, owner):
        self.color = color      # 0 red, 1 green, 2 blue, 3 yellow, 4 none
        self.type = type        # 0 number, 1 action, 2 wildcard
        self.value = number    # holds the card name
        self.draw_amount = draw_amount  # 0 default
        self.used = 0
        self.changeColor = changes_color
        self.points = points
        self.owner = owner
    
    def __getstate__(self):
        # Return a dictionary of the card's attributes to be pickled
        return self.__dict__

    def __setstate__(self, state):
        # Restore the card's attributes from the pickled state
        self.__dict__.update(state)    

class Player:
    def __init__(self, cards, id):
        self.id = id
        self.cards = cards      # array
        self.playableCards = 0
        self.number_of_cards = len(cards)
        self.score = 0
        self.trueskill = Rating(mu=30, sigma=8)
        self.wins = 0
        self.isCheater = 0      # cheater AI will be able to see everyone's hand

# This class named Table will contain the played cards and who played them    
class Table:
    def __init__(self, deck):
        self.deck = deck
        self.alive = {}
        self.dead = {}
        self.cards = []
        self.turn = 0
        self.direction = True      # 0 clockwise , 1 = counter clockwise
        self.lastPlacementBy = -1 # Who is the player that placed the top card
        self.turns_to_be_skipped = 0
        self.reverses = 0
        self.to_be_drawn = 0




NUMBER_OF_DECKS = config.NUMBER_OF_DECKS
NUMBER_OF_PLAYERS = config.NUMBER_OF_PLAYERS
NUMBER_OF_INITIAL_CARDS = config.NUMBER_OF_INITIAL_CARDS

NUMBER_OF_THREADS = config.NUMBER_OF_THREADS   # to be implemented
NUMBER_OF_SIMULATIONS_PER_THREAD = config.NUMBER_OF_SIMULATIONS_PER_THREAD  # type 0 to make it endless

PLAYER_ID = config.PLAYER_ID

# Rules
ONLY_ONE_PLAYER_CAN_WIN = config.ONLY_ONE_PLAYER_CAN_WIN


print("------------")
print("------------")
print("------------")
print("------------")
print("------------")



def startGame():

    simulation = 0
    
    # Pickle data
    #game_data = {}


    # Declare table
    table = Table([])

    # create players
    table = spawnPlayers(table)
    

    # Run the simulation
    while (simulation < NUMBER_OF_SIMULATIONS_PER_THREAD and NUMBER_OF_SIMULATIONS_PER_THREAD != 0) or (NUMBER_OF_SIMULATIONS_PER_THREAD == 0):

        # Reset table
        table.deck = []
        table.alive.update(table.dead)
        table.dead.clear()
        table.cards = []
        table.turn = 0
        table.direction = True      # 0 clockwise , 1 = counter clockwise
        table.lastPlacementBy = -1 # Who is the player that placed the top card
        table.turns_to_be_skipped = 0
        table.reverses = 0
        table.to_be_drawn = 0
        
        # Reset players
        for i in table.alive:
            table.alive[i].cards = []
            table.alive[i].playableCards = 0
            table.alive[i].number_of_cards = 0
        
        # Create deck
        table.deck = shuffleDeck(generateDeck())
        
        # Important check
        if NUMBER_OF_PLAYERS * NUMBER_OF_INITIAL_CARDS > len(table.deck):
            print("[ERROR] NUMBER_OF_PLAYERS * NUMBER_OF_INITIAL_CARDS > len(deck)")
            print("Either lower NUMBER_OF_PLAYERS or NUMBER_OF_INITIAL_CARDS")
            break
        
        # Place the top card of the draw pile face-up in the middle of the table : table.top_card
        table.cards.append(table.deck.pop(0))

        # Deal 7 cards to each player
        table = dealCards(table)
        

        # Run the game
        winners = 0
        turns = 0

        #game_data["Simulation_"+str(simulation)] = { 'Turns': {} }

        
        while True:
            
            # failsafe
            if len(table.deck) == 0 and len(table.cards) == 0:
                # Delete current simulation info from data
                #game_data["Simulation_"+str(simulation)]["Turns"] = {}
                break

            # check if draw pile is empty
            if len(table.deck) == 0:
                # Shuffle the discard pile and make it the new draw pile
                temp = table.cards.pop(0)
                table.deck = shuffleDeck(table.cards)
                table.cards.append(temp)

            hand = table.alive[table.turn].cards

            #print("-------------------------------- Alive: ",count , " --------- must_be_picked: ",table.to_be_drawn)

            # handle skip turn
            while(table.turns_to_be_skipped > 0 and table.lastPlacementBy != table.turn):
                table.turns_to_be_skipped += -1
                table = skipTurn(table, table.turn) # end turn

            # Player's turn starts here
            turns += 1

            # IF the current player has a playable card:
            if canPlayerPlay(hand, table):
                
                table, hand = logic(table, hand)
                
            else:
                # Draw

                # If the player can't respond to a draw card, then this will handle Draw +2, +4, +10, ... very well
                draw_amount = 1
                if table.to_be_drawn > 0:
                    draw_amount = table.to_be_drawn
                    table.to_be_drawn = 0

                drawn = drawCards(table.deck, draw_amount, table.turn)
                for card in drawn:
                    hand.append(card)

                table.alive[table.turn].cards = hand
                
                # IF the drawn card is playable:
                if canPlayerPlay(hand, table):
                    table, hand = logic(table, hand)


            # handle Reverses
            while (table.reverses > 0 and table.lastPlacementBy != table.turn):
                table.direction = not table.direction
                table.reverses += -1

            turn_backup = table.turn
            
            table = skipTurn(table, table.turn) # end turn
            
            #print(len(table.alive[turn_backup].cards))
            # IF a player has no cards left:
            if (len(table.alive[turn_backup].cards) <= 0):
                # Game over
                table.alive[turn_backup].wins += 1
                #print(table.alive[turn_backup].wins)
                # Player with no cards left wins
                points = 0
                for player in table.alive:
                    if table.alive[player] != table.alive[turn_backup]:
                        for card in table.alive[player].cards:
                            points += card.points
                
                table.alive[turn_backup].score = points
                
                #increase trueskill
                table = update_trueskill(table, turn_backup)

                # move player into dead players
                player = table.alive[turn_backup]
                table.dead[turn_backup] = player

                # remove the current player from alive players
                del table.alive[turn_backup]
                winners += 1            

            # store turn data
            #game_data["Simulation_"+str(simulation)]["Turns"][turns] = turn_data
                    # Check for the end of the simulation
            if (ONLY_ONE_PLAYER_CAN_WIN and winners >= 1) or (not ONLY_ONE_PLAYER_CAN_WIN and winners >= NUMBER_OF_PLAYERS - 1):
                winners = 0
                break

        #avg_turns.append(turns)

        if NUMBER_OF_SIMULATIONS_PER_THREAD > 0:
            simulation += 1
        

    
    # END of simulation
    table.alive.update(table.dead)
    table.dead.clear()

    for player in table.alive:
        print("Player: ",player," - TR: ",table.alive[player].trueskill," - Wins: ",table.alive[player].wins," - Win%: ",table.alive[player].wins / NUMBER_OF_SIMULATIONS_PER_THREAD * 100)

    # Store all game data into file
    #with open("data.parquet", "wb") as file:
    # Convert column names to strings

    """
    json_string = json.dumps(game_data)
    print(json_string)
    game_data_str = {str(key): value for key, value in game_data.items()}
    # Create DataFrame
    df = pd.DataFrame(game_data_str)
    # Define Parquet file path
    parquet_file = "game_data.parquet"
    # Write DataFrame to Parquet
    table = pa.Table.from_pandas(df)
    pq.write_table(table, parquet_file)
    """


# implement threads
startGame()


#print("Avg turns: ",np.mean(avg_turns), " - Minutes: ",np.mean(avg_turns) * 2 / 60)



"""
Things done so far:
    create shuffled deck
    spawn players
    give each player 7 cards
    implement canPlay logic

    implement game_data in pickle format
"""