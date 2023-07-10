import config
import random
import tensorflow as tf
import numpy as np
import trueskill

from game_utility import get_game_data

NUMBER_OF_DECKS = config.NUMBER_OF_DECKS
NUMBER_OF_PLAYERS = config.NUMBER_OF_PLAYERS
NUMBER_OF_INITIAL_CARDS = config.NUMBER_OF_INITIAL_CARDS

ENABLE_LOGGING = config.ENABLE_LOGGING

TOTAL_SIMULATIONS = config.TOTAL_SIMULATIONS
PLAYER_ID = config.PLAYER_ID
# Rules
ONLY_ONE_PLAYER_CAN_WIN = config.ONLY_ONE_PLAYER_CAN_WIN


def skipTurn(table, currentTurn):
    remaining_players = table.alive.keys()
    keys_list = list(remaining_players)
    keys_list = sorted(remaining_players)
    num_players = len(keys_list)

    # Get the current index
    current_index = keys_list.index(currentTurn)
    

    # Get the next index
    next_index = 0
    if num_players == 2 and (table.cards[len(table.cards) -1].value == "Reverse" or table.cards[len(table.cards) -1].value == "Reverse") and table.cards[len(table.cards) -1].used == 0:  # Only two players
        
        next_index = current_index  # Skip the next player
        table.cards[len(table.cards) -1].used = 1
        
    else:
        if table.direction:
            next_index = (current_index + 1) % len(keys_list)
        else:
            next_index = (current_index - 1) % len(keys_list)
    
    table.turn = keys_list[next_index]
    return table






def canPlayerPlay(hand, table):

    if len(table.cards) < 1:
        return False
    

    # need to draw cards ?
    if table.to_be_drawn > 0:
        for card in hand:
            if card.value == table.cards[len(table.cards) - 1].value:
                return True
        return False

    # first time playing ?
    if table.lastPlacementBy != table.alive[table.turn].id:
        for card in hand:
            if card.type == 2:
                return True
            elif card.value == table.cards[len(table.cards) - 1].value:
                return True
            elif card.color == table.cards[len(table.cards) - 1].color:
                return True
    elif table.lastPlacementBy != table.alive[table.turn].id: # 2nd time playing
        for card in hand:
            if card.value == table.cards[len(table.cards) - 1].value:
                return True
    
    # can't play anything, must draw
    return False

def playCard(hand, table):
    playableCards = []

    value = table.cards[len(table.cards) - 1].value
    color = table.cards[len(table.cards) - 1].color

    if table.lastPlacementBy != table.turn and table.to_be_drawn == 0:    
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
    
    print("impossible")
    # This should never hit
    return 9999



def changeColor(table):
    possibilities = []

    if len(table.alive[table.turn].cards) > 0:

        for card in table.alive[table.turn].cards:
            possibilities.append(card.color)

        return possibilities[random.randrange(0, len(possibilities))]
    else:
        return random.randint(1,4)


def canCardBePlayed(table, hand, index):
        card = hand[index]
        hand = []
        hand.append(card)
        return canPlayerPlay(hand, table) # will return true of false

def logic(table, hand, game_data, turns, p_count, draw_amount):
    
    while canPlayerPlay(hand, table):
        
        
        index = playCard(hand, table)
        
        # Should never be hit
        if index == 9999:
            continue

        # check if selected card is playable
        # when ai will be implemented, it will probably try to use an illegal card
        if not canCardBePlayed(table, hand, index):
            print("Illegal move")
            continue

        if table.turn == PLAYER_ID:
            hand_str = "[CARDS] "
            for card in hand:
                hand_str += str(hand.index(card))+" card: [" + str(card.value) + "  -  " + str(card.color) + "] /// "
            print(hand_str)                        
            print("Suggested: ",index)
            index = int(input("pick index: "))

        hand_data = hand.copy()
        
        # check if direction must be reversed
        if hand[index].value == "Reverse":
            #hand[index].used = 1
            table.direction = not table.direction
            table.cards[len(table.cards) - 1].used = 0
        
        # check if player must be skipped
        if hand[index].value == "Skip":
            table.turns_to_be_skipped += 1

        # add to the bank
        #if hand[index].draw_amount > 0:
        table.to_be_drawn += hand[index].draw_amount
        
        # set who placed the card
        table.lastPlacementBy = table.alive[table.turn].id

        # put used card on the card pile
        table.cards.append(hand.pop(index))
        table.alive[table.turn].cards = hand

        if ENABLE_LOGGING:
            game_data = get_game_data(game_data, table, turns, p_count, hand_data, draw_amount)

        # check if color must be changed
        if table.cards[len(table.cards) - 1].color == 5:
            table.cards[len(table.cards) - 1].color = changeColor(table)
        
        
        return table, hand, game_data



def update_trueskill(table, winning_player_id):
    
    players = list(table.alive.values())
    
    env = trueskill.TrueSkill()

    ratings = []
    for player in players:
        player_rating = env.create_rating(player.trueskill)
        player_rating_group = [player_rating]  # Wrap the rating in a list
        ratings.append(player_rating_group)

    # index of the winning player
    winning_player_index = [player.id for player in players].index(winning_player_id)

    # list of ranks for all players
    ranks = [1] * len(players)  # SEt all ranks to 1 initially
    ranks[winning_player_index] = 0  # Set the rank of the winning player to 0

    # update the TrueSkill ratings based on the outcome
    new_ratings = env.rate(ratings, ranks=ranks)

    for i, player in enumerate(players):
        player.trueskill = new_ratings[i][0].mu

    table.alive = {player.id: player for player in players}

    return table
