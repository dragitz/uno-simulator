import config
import random

import trueskill
from trueskill import Rating
from game_utility import generateDeck, shuffleDeck, drawCards, spawnPlayers, dealCards

NUMBER_OF_DECKS = config.NUMBER_OF_DECKS
NUMBER_OF_PLAYERS = config.NUMBER_OF_PLAYERS
NUMBER_OF_INITIAL_CARDS = config.NUMBER_OF_INITIAL_CARDS

NUMBER_OF_THREADS = config.NUMBER_OF_THREADS   # to be implemented
NUMBER_OF_SIMULATIONS_PER_THREAD = config.NUMBER_OF_SIMULATIONS_PER_THREAD  # type 0 to make it endless

PLAYER_ID = config.PLAYER_ID

# Rules
ONLY_ONE_PLAYER_CAN_WIN = config.ONLY_ONE_PLAYER_CAN_WIN




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
