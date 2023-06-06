# Uno cards game simulator with deep learning.
# Model saving and loading using keras and tensorflow.
# Uses threads to simulate multiple games
# Tested on Windows 10

"""
TrueSkill analysis (100k games):
- Random moves with mu=30 and sigma=8, and multiple people can win, leads to trueskill --> 28 - 38
- Random moves with mu=30 and sigma=8, and only 1 person can win, leads to trueskill --> 25 - 33
"""

"""
    TODO:
        - Implement (efficient) data collection with periodical saving
        - Create deep learning model
        - Compute TR of model
        - Create a pygame interface for playing vs bots
        - Implement TCP to play with friends via LAN (Radmin, Hamachi, ...)
"""

import random
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import trueskill
from trueskill import Rating, rate

NUMBER_OF_DECKS = 1
NUMBER_OF_PLAYERS = 4
NUMBER_OF_INITIAL_CARDS = 7

NUMBER_OF_THREADS = 1   # to be implemented
NUMBER_OF_SIMULATIONS_PER_THREAD = 100000   # type 0 to make it endless

PLAYER_ID = 900

# Rules
ONLY_ONE_PLAYER_CAN_WIN = True


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


print("------------")
print("------------")
print("------------")
print("------------")
print("------------")



#    GAME UTILITY
def generateDeck():
    deck = []
    
    colors = ["Red","Green","Blue","Yellow"]
    
    values = [i for i in range(10)]
    action_cards = ["Draw Two", "Skip", "Reverse"]
    wilds = ["Wild","Wild Draw Four"]

    for _ in range(NUMBER_OF_DECKS):
        for color in colors:
            index_of_color = colors.index(color)

            for value in values:
                deck.append(Card(index_of_color, 0, value, 0, 0, value, 99))
                if value != 0:
                    deck.append(Card(index_of_color, 0, value, 0, 0, value, 99))

        for _ in range(NUMBER_OF_DECKS):
            for color in colors:
                index_of_color = colors.index(color)

                for value in action_cards:
                    if value == "Draw Two":
                        # (color, type, number, draw_amount, changes_color, points, owner):
                        deck.append(Card(index_of_color, 1, value, 2, 0, 20, 99))
                        deck.append(Card(index_of_color, 1, value, 2, 0, 20, 99))
                    else:
                        deck.append(Card(index_of_color, 1, value, 0, 0, 20, 99))
                        deck.append(Card(index_of_color, 1, value, 0, 0, 20, 99))

        for _ in range(4):
            # (color, type, number, draw_amount, changes_color, points, owner):
            deck.append(Card(4, 2, wilds[0], 0, 1, 50, 99))
            deck.append(Card(4, 2, wilds[1], 4, 1, 50, 99))

    return deck

def shuffleDeck(deck):
    for i in range(len(deck)):
        rand = random.randint(0, len(deck)-1)
        deck[i], deck[rand] = deck[rand], deck[i]
    return deck

def drawCards(deck, amount, owner):
    cardsDrawn = []

    # deck has no cards, should never get executed
    if len(deck) < 1:
        print("ERROR: no more available cards in deck")
        return cardsDrawn
    
    # requested too many cards
    if amount > len(deck):
        for _ in range(len(deck)-1):
            deck[0].owner = owner
            deck[0].used = 0
            cardsDrawn.append(deck.pop(0))
    else:
        for _ in range(amount):
            deck[0].owner = owner
            deck[0].used = 0
            cardsDrawn.append(deck.pop(0))

    return cardsDrawn

def spawnPlayers(table):
    for i in range(NUMBER_OF_PLAYERS):
        table.alive[i] = Player([], i)
    
    return table

def dealCards(table):
    for i in range(NUMBER_OF_PLAYERS):
        table.alive[i].cards = drawCards(table.deck, NUMBER_OF_INITIAL_CARDS + 1, i)
    
    return table

#    GAME LOGIC
def skipTurn(table, currentTurn):
    remaining_players = table.alive.keys()
    
    keys_list = list(remaining_players)

    # Get the current index
    current_index = keys_list.index(currentTurn)

    # Get the next index
    next_index = 0
    if table.direction:
        next_index = (current_index + 1) % len(keys_list)
    else:
        next_index = (current_index - 1) % len(keys_list)
    
    table.turn = keys_list[next_index]

    return table

def canPlayerPlay(hand, table):

    if len(table.cards) < 1:
        return False
    
    # in case we must not draw
    if table.lastPlacementBy != table.alive[table.turn].id and table.to_be_drawn == 0:
        for card in hand:
            if card.type == 2:
                return True
            if card.value == table.cards[len(table.cards) - 1].value:
                return True
            if card.color == table.cards[len(table.cards) - 1].color:
                return True
    else:
        for card in hand:
            if card.value == table.cards[len(table.cards) - 1].value:
                return True
                    
    return False

def playCard(hand, table):
    playableCards = []

    value = table.cards[len(table.cards) - 1].value
    color = table.cards[len(table.cards) - 1].color

    if table.lastPlacementBy != table.alive[table.turn].id and table.to_be_drawn == 0:    
        for card in hand:
            if card.type == 2:
                playableCards.append(card)
                continue
            if card.value == value:
                playableCards.append(card)
                continue
            if card.color == color:
                playableCards.append(card)
                continue
    else:
        for card in hand:
            if card.value == value:
                playableCards.append(card)


    if len(playableCards) > 0:
        if len(playableCards) > 1:
            index = playableCards[random.randrange(0, len(playableCards) - 1)]
            return hand.index(index)
        else:
            return hand.index(playableCards[0])
    
    
    return 9999
 
def changeColor(table):
    possibilities = []

    if len(table.alive[table.turn].cards) > 0:

        for card in table.alive[table.turn].cards:
            possibilities.append(card.color)

        return possibilities[random.randrange(0, len(possibilities))]
    else:
        return random.randint(0,3)

def canCardBePlayed(table, hand, index):
        card = hand[index]
        hand = []
        hand.append(card)
        return canPlayerPlay(hand, table) # will return true of false

def logic(table, hand):
    while canPlayerPlay(hand, table):
        
        if not canPlayerPlay(hand, table):
            break

        index = playCard(hand, table)
        
        # check if selected card is playable
        # when ai will be implemented, it will probably try to use an illegal card
        if not canCardBePlayed(table, hand, index):
            #print("Illegal move")
            continue

        if table.turn == PLAYER_ID:
            hand_str = "[CARDS] "
            for card in hand:
                hand_str += str(hand.index(card))+" card: [" + str(card.value) + "  -  " + str(card.color) + "] /// "
            print(hand_str)                        
            print("Suggested: ",index)
            index = int(input("pick index: "))

        #print(table.direction)
        #print("["+str(table.turn)+"] Played: ",hand[index].value," - Color: ",hand[index].color)
        #print("Player (a): ", table.turn,"Top card: ",table.cards[len(table.cards) - 1].value, " - Color: ",table.cards[len(table.cards) - 1].color, "    who: ",table.lastPlacementBy)
        table.lastPlacementBy = table.alive[table.turn].id

        # check if direction must be reversed
        if hand[index].value == "Reverse" and table.cards[len(table.cards) - 1].used == 0:
            hand[index].used = 1
            table.direction = not table.direction

        # check if direction must be reversed
        if hand[index].value == "Reverse":
            table.reverses += 1
        
        # check if player must be skipped
        if hand[index].value == "Skip":
            table.turns_to_be_skipped += 1

        # add to the bank
        if hand[index].draw_amount > 0:
            table.to_be_drawn += hand[index].draw_amount


        # put used card on the card pile
        table.cards.append(hand.pop(index))
        table.alive[table.turn].cards = hand

        # check if color must be changed
        if table.cards[len(table.cards) - 1].color == 4:
            table.cards[len(table.cards) - 1].color = changeColor(table)
        
        
        return table, hand





def update_trueskill(table, winning_player_id):
    # Extract the players from the table
    players = list(table.alive.values())

    # Create a TrueSkill environment
    env = trueskill.TrueSkill()

    # Create TrueSkill rating objects for each player
    ratings = []
    for player in players:
        player_rating = env.create_rating(player.trueskill)
        player_rating_group = [player_rating]  # Wrap the rating in a list
        ratings.append(player_rating_group)

    # Find the index of the winning player
    winning_player_index = [player.id for player in players].index(winning_player_id)

    # Create a list of ranks for all players
    ranks = [0] * len(players)
    ranks[winning_player_index] = 1

    # Update the TrueSkill ratings based on the outcome
    new_ratings = env.rate(ratings, ranks=ranks)

    # Update the TrueSkill score for each player
    for i, player in enumerate(players):
        player.trueskill = new_ratings[i][0].mu
        #print(player.trueskill )

    # Update the table
    table.alive = {player.id: player for player in players}

    # Return the updated table
    return table




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