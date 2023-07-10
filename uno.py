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
        x Implement (efficient) data collection with periodical saving
        - Create deep learning model
        x Compute TR of model
        - Create a pygame interface for playing vs bots
        - Implement TCP to play with friends via LAN (Radmin, Hamachi, ...)
"""


import numpy as np
import pandas as pd
import random
import timeit
import config

import tensorflow as tf
from tensorflow import keras

from game_utility import generateDeck, shuffleDeck, drawCards, spawnPlayers, dealCards, logData, get_game_data
from game_logic import skipTurn, canPlayerPlay, logic, update_trueskill
from trueskill import Rating



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
        self.direction = True      # 0 clockwise , 1 = counter clockwise
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


# Logging
ENABLE_LOGGING = config.ENABLE_LOGGING
ONLY_LOG_WINNING_GAMES = config.ONLY_LOG_WINNING_GAMES

ENABLE_MAX_TURNS = config.ENABLE_MAX_TURNS
MAX_TURNS = config.MAX_TURNS



print("------------")
print("------------")
print("------------")
print("------------")
print("------------")




def startGame():

    simulation = 0

    # Declare table
    table = Table([])

    # create players
    table = spawnPlayers(table)
    
    # Run the simulation
    while (simulation < TOTAL_SIMULATIONS and TOTAL_SIMULATIONS != 0) or (TOTAL_SIMULATIONS == 0):

        game_data = {
            'game_turn': [],
            'top_card_id': [],
            #'top_card_value': [],
            'top_card_color': [],
            'top_card_type': [],
            'top_card_draw_amount': [],
            'top_card_points': [],
            'player_id': [],
            'drawn_cards': [],
            'has_won': [],
            'p_count': [],
            'dir': []
        }

        
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
        table.cards[0].used = 1

        # Deal 7 cards to each player
        table = dealCards(table)

        # Run the game
        winners = 0
        turns = 0

        if ENABLE_LOGGING:
            game_data["game_turn"].append(0)
            game_data["top_card_id"].append(table.cards[len(table.cards) - 1].card_id)
            #game_data["top_card_value"].append(str(table.cards[len(table.cards) - 1].value))
            game_data["top_card_color"].append(table.cards[len(table.cards) - 1].color)
            game_data["top_card_type"].append(table.cards[len(table.cards) - 1].type)
            game_data["top_card_draw_amount"].append(table.cards[len(table.cards) - 1].draw_amount)
            game_data["top_card_points"].append(table.cards[len(table.cards) - 1].points)
            game_data["player_id"].append(table.lastPlacementBy)
            game_data["drawn_cards"].append(0)
            game_data["has_won"].append(0)
            game_data["p_count"].append(NUMBER_OF_PLAYERS)
            game_data["dir"].append(table.direction)

            for i in range(30):
                game_data["card"+str(i)] = []
                game_data["card"+str(i)].append(0)

        while True:
            
            # failsafe
            if len(table.deck) == 0 and len(table.cards) == 0:
                break

            # check if draw pile is empty ( must be set to 1 otherwise we get array issues)
            if len(table.deck) <= 1:
                # Shuffle the discard pile and make it the new draw pile
                temp = table.cards.pop(0)
                table.deck = shuffleDeck(table.cards)
                table.cards.append(temp)

            hand = table.alive[table.turn].cards

            p_count = len(table.alive)
            
            #print("-------------------------------- Alive: ",count , " --------- must_be_picked: ",table.to_be_drawn)


            # handle skip turn
            while(table.turns_to_be_skipped > 0):
                table.turns_to_be_skipped -= 1
                table = skipTurn(table, table.turn) # end turn

            # Player's turn starts here
            turns += 1

            # IF the current player has a playable card:
            if canPlayerPlay(hand, table):

                table, hand, game_data = logic(table, hand, game_data, turns, p_count, 0)
                table.alive[table.turn].performance += 1
                
                if ENABLE_LOGGING:
                    #game_data = get_game_data(game_data, table, turns, p_count, hand_data, 0)
                    pass

            else:
                # Draw

                # If the player can't respond to a draw card, then this will handle Draw +2, +4, +10, ... very well
                draw_amount = 1
                if table.to_be_drawn > 0:
                    draw_amount = table.to_be_drawn
                    table.to_be_drawn = 0

                table.alive[table.turn].performance -= draw_amount

                drawn = drawCards(table.deck, draw_amount, table.turn)
                for card in drawn:
                    hand.append(card)

                table.alive[table.turn].cards = hand

                # IF the drawn card is playable:
                if canPlayerPlay(hand, table):
                    table, hand, game_data = logic(table, hand, game_data, turns, p_count, draw_amount)
                    table.alive[table.turn].performance += 1
                
            turn_backup = table.turn
            
            table = skipTurn(table, table.turn) # end turn
            
            
            # IF a player has no cards left:
            if (len(table.alive[turn_backup].cards) <= 0):
                
                #table = skipTurn(table, table.turn) # end turn

                # Game over
                table.alive[turn_backup].wins += 1

                # Player with no cards left wins
                points = 0
                for player in table.alive:
                    if table.alive[player] != table.alive[turn_backup]:
                        for card in table.alive[player].cards:
                            points += card.points
                
                table.alive[turn_backup].score = points
                
                #increase trueskill
                table = update_trueskill(table, turn_backup)

                # change has_won of this current player
                for index, player_id in enumerate(game_data["player_id"]):
                    if turn_backup == player_id:
                        game_data["has_won"][index] = 1

                # move player into dead players
                player = table.alive[turn_backup]
                table.dead[turn_backup] = player

                # remove the current player from alive players
                del table.alive[turn_backup]
                winners += 1

            # end conditions
            if (ONLY_ONE_PLAYER_CAN_WIN and winners > 0) or (
                not ONLY_ONE_PLAYER_CAN_WIN and winners >= NUMBER_OF_PLAYERS - 1) or (
                ENABLE_MAX_TURNS and turns > MAX_TURNS):
                
                break

        if TOTAL_SIMULATIONS > 0:
            simulation += 1

        if ((ONLY_LOG_WINNING_GAMES and winners > 0) or (not ONLY_LOG_WINNING_GAMES)) and ENABLE_LOGGING:
            logData(game_data, simulation)
            pass

    # END of simulation
    table.alive.update(table.dead)
    table.dead.clear()

    for player in table.alive:
        print("Player: ",player," - TS: ",table.alive[player].trueskill," - Wins: ",table.alive[player].wins,"  Perf: ",table.alive[player].performance)

#startGame()

execution_time = timeit.timeit(startGame, number=1)
print("Execution time:", execution_time, "seconds")