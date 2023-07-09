import os
import numpy as np
import config
import random
from trueskill import Rating

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

#from uno import Card, Player, Table


# Yes it's being defined twice :) I've never dealt with circular imports

class Card:
    def __init__(self, color, type, action_type, value, draw_amount, changes_color, points, owner):
        self.color = color      # 1 red, 2 green, 3 blue, 4 yellow, 5 none
        self.type = type        # 0 number, 1 action, 2 wildcard
        self.action_type = action_type # 0 none, 1 "Draw Two", 2 "Skip", 3 "Reverse"
        self.draw_amount = draw_amount  # 0 default
        self.value = value     # holds the card name
        self.card_id = int(str(color)+str(type)+str(action_type)+str(points)) # this number will be fed into the neural network
        self.used = 0
        self.changeColor = changes_color
        self.points = points
        self.owner = owner
    
    # Card_id structure
    # Draw two, yellow = 411
    # Skip, green = 212
    # Wild card

    def __getstate__(self):
        # Return a dictionary of the card's attributes to be pickled
        return self.__dict__

    def __setstate__(self, state):
        # Restore the card's attributes from the pickled state
        self.__dict__.update(state)    

class Player:
    def __init__(self, cards, id, AI_LEVEL):
        self.id = id
        self.cards = cards      # array
        self.number_of_cards = len(cards)
        self.score = 0
        self.trueskill = Rating(mu=30, sigma=8)
        self.wins = 0
        self.isCheater = 0      # cheater AI will be able to see everyone's hand
        self.AI_LEVEL = AI_LEVEL       # 0 = basic ;; 1 = tensorflow ;; 2 = debug (player)
        self.performance = 0
        
# This class named Table will contain the played cards and who played them    
class Table:
    def __init__(self, deck):
        self.deck = deck
        self.alive = {}
        self.dead = {}
        self.cards = []
        self.turn = 0
        self.direction = True      # true = clockwise , false = counter clockwise
        self.lastPlacementBy = -1 # Who is the player that placed the top card
        self.turns_to_be_skipped = 0
        self.reverses = 0
        self.to_be_drawn = 0



NUMBER_OF_DECKS = config.NUMBER_OF_DECKS
NUMBER_OF_PLAYERS = config.NUMBER_OF_PLAYERS
NUMBER_OF_INITIAL_CARDS = config.NUMBER_OF_INITIAL_CARDS

TOTAL_SIMULATIONS = config.TOTAL_SIMULATIONS

PLAYER_ID = config.PLAYER_ID

# Rules
ONLY_ONE_PLAYER_CAN_WIN = config.ONLY_ONE_PLAYER_CAN_WIN


def logData(data, table_number):
    
    #print("Saving ... "+str(table_number))

    df = pd.DataFrame(data)
    schema = pa.schema([
        ('game_turn', pa.int64()),
        ('top_card_id', pa.int64()),
        ('top_card_value', pa.string()),
        ('player_id', pa.int64()),
        ('top_card_color', pa.int64()),
        ('top_card_type', pa.int64()),
        ('top_card_draw_amount', pa.int64()),
        ('top_card_points', pa.int64()),
        ('drawn_cards', pa.int64()),
        ('has_won', pa.int64()),
        ('p_count', pa.int64()),
        ('dir', pa.int64()),
        ('card0', pa.int64()),
        ('card1', pa.int64()),
        ('card2', pa.int64()),
        ('card3', pa.int64()),
        ('card4', pa.int64()),
        ('card5', pa.int64()),
        ('card6', pa.int64()),
        ('card7', pa.int64()),
        ('card8', pa.int64()),
        ('card9', pa.int64()),
        ('card10', pa.int64()),
        ('card11', pa.int64()),
        ('card12', pa.int64()),
        ('card13', pa.int64()),
        ('card14', pa.int64()),
        ('card15', pa.int64()),
        ('card16', pa.int64()),
        ('card17', pa.int64()),
        ('card18', pa.int64()),
        ('card19', pa.int64()),
        ('card20', pa.int64()),
        ('card21', pa.int64()),
        ('card22', pa.int64()),
        ('card23', pa.int64()),
        ('card24', pa.int64()),
        ('card25', pa.int64()),
        ('card26', pa.int64()),
        ('card27', pa.int64()),
        ('card28', pa.int64()),
        ('card29', pa.int64())
        
    ])
    
    table = pa.Table.from_pandas(df, schema=schema)

    # Save the table as a Parquet file
    pq.write_table(table, 'dataset/data'+str(table_number)+'.parquet')

def get_game_data(game_data, table, turns, p_count, hand_data, draw_amount):

    
    game_data["game_turn"].append(turns)
    game_data["top_card_id"].append(table.cards[len(table.cards) - 1].card_id)
    game_data["top_card_value"].append(str(table.cards[len(table.cards) - 1].value))
    game_data["top_card_color"].append(table.cards[len(table.cards) - 1].color)
    game_data["top_card_type"].append(table.cards[len(table.cards) - 1].type)
    game_data["top_card_draw_amount"].append(table.cards[len(table.cards) - 1].draw_amount)
    game_data["top_card_points"].append(table.cards[len(table.cards) - 1].points)
    game_data["player_id"].append(table.turn)
    game_data["drawn_cards"].append(draw_amount) 
    game_data["has_won"].append(0) 
    game_data["p_count"].append(p_count)
    game_data["dir"].append(table.direction)

    length = len(hand_data)

    for x in range(30):
        if x >= length:
            game_data["card"+str(x)].append(0)
        else:
            game_data["card"+str(x)].append(hand_data[x].card_id)

        
        

    

    return game_data

def generateDeck():
    deck = []
    
    colors = ["Red","Green","Blue","Yellow"]
    
    values = [i for i in range(10)]
    action_cards = ["Draw Two", "Skip", "Reverse"]
    wilds = ["Wild","Wild Draw Four"]

    default_owner = 999

    for _ in range(NUMBER_OF_DECKS):
        for color in colors:
            index_of_color = colors.index(color)
            index_of_color += 1 # Index must start form 1, not 0

            for value in values:          
                deck.append(Card(index_of_color, 0, 0, value, 0, 0, value, default_owner))
                if value != 0:
                    deck.append(Card(index_of_color, 0, 0, value, 0, 0, value, default_owner))

        for _ in range(NUMBER_OF_DECKS):
            for color in colors:
                index_of_color = colors.index(color)
                index_of_color += 1 # Index must start form 1, not 0

                for value in action_cards:
                    index_of_type = action_cards.index(value)
                    if value == "Draw Two":
                        # (color, type, value, draw_amount, changes_color, points, owner):
                        # (color, type, action_type, value, draw_amount, changes_color, points, owner)
                        deck.append(Card(index_of_color, 1, index_of_type, value, 2, 0, 20, default_owner))
                        deck.append(Card(index_of_color, 1, index_of_type, value, 2, 0, 20, default_owner))
                    else:
                        deck.append(Card(index_of_color, 1, index_of_type, value, 0, 0, 20, default_owner))
                        deck.append(Card(index_of_color, 1, index_of_type, value, 0, 0, 20, default_owner))
                        

        for _ in range(4):
            # (color, type, action_type, value, draw_amount, changes_color, points, owner)
            deck.append(Card(5, 2, 0, wilds[0], 0, 1, 50, default_owner))
            deck.append(Card(5, 2, 0, wilds[1], 4, 1, 50, default_owner))

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
        table.alive[i] = Player([], i, 1)
    
    return table

def dealCards(table):
    for i in range(NUMBER_OF_PLAYERS):
        table.alive[i].cards = drawCards(table.deck, NUMBER_OF_INITIAL_CARDS + 1, i)
    
    #table.alive = sorted(table.alive)
    return table