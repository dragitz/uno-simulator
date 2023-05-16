# Uno cards game simulator with deep learning.
# Model saving and loading using keras and tensorflow.
# Uses threads to simulate multiple games
# Tested on Windows 10

import random
import numpy as np
import pickle

NUMBER_OF_DECKS = 1
NUMBER_OF_PLAYERS = 4
NUMBER_OF_INITIAL_CARDS = 7

NUMBER_OF_THREADS = 1
NUMBER_OF_SIMULATIONS_PER_THREAD = 53000   # type 0 to make it endless

PLAYER_ID = 90

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
        self.isAlive = 1        # 0 = won
        self.isCheater = 0      # cheater AI will be able to see everyone's hand

# This class named Table will contain the played cards and who played them    
class Table:
    def __init__(self, deck):
        self.deck = deck
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


def spawnPlayers(deck, playerList):
    for i in range(NUMBER_OF_PLAYERS):
        playerList.append(Player(drawCards(deck, NUMBER_OF_INITIAL_CARDS + 1, i), i))


def skipTurn(table, playerList):
    amount = len(playerList) - 1
    # 0 - clockwise
    # 1 - counter clockwise
    if table.direction:
        if table.turn < amount:
            table.turn += 1
        else:
            table.turn = 0
    else:
        if table.turn == 0:
            table.turn = amount
        else:
            table.turn -= 1
    
    
    return table

def canPlayerPlay(hand, table, playerList):

    if len(table.cards) < 1:
        return False
    
    # in case we must not draw
    if table.lastPlacementBy != playerList[table.turn].id and table.to_be_drawn == 0:
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


def playCard(hand, table, playerList):
    playableCards = []

    value = table.cards[len(table.cards) - 1].value
    color = table.cards[len(table.cards) - 1].color

    if table.lastPlacementBy != playerList[table.turn].id and table.to_be_drawn == 0:    
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

    
def changeColor(playerList, table):
    possibilities = []

    if len(playerList[table.turn].cards) > 0:

        for card in playerList[table.turn].cards:
            possibilities.append(card.color)

        return possibilities[random.randrange(0, len(possibilities))]
    else:
        return random.randint(0,3)

def canCardBePlayed(table, hand, index, playerList):
        card = hand[index]
        hand = []
        hand.append(card)
        return canPlayerPlay(hand, table, playerList) # will return true of false

def logic(table, playerList, hand):
    while canPlayerPlay(hand, table, playerList):
        
        if not canPlayerPlay(hand, table, playerList):
            break

        index = playCard(hand, table, playerList)
        
        # check if selected card is playsble
        # when ai will be implemented, it will probably try to use an illegal card
        if not canCardBePlayed(table, hand, index, playerList):
            #print("Illegal move")
            continue

        if table.turn == PLAYER_ID:
            hand_str = "[CARDS] "
            for card in hand:
                hand_str += str(hand.index(card))+" card: [" + str(card.value) + "  -  " + str(card.color) + "] /// "
            #print(hand_str)                        
            #print("Suggested: ",index)
            index = int(input("pick index: "))

        #print(table.direction)
        #print("["+str(table.turn)+"] Played: ",hand[index].value," - Color: ",hand[index].color)
        #print("Player (a): ", table.turn,"Top card: ",table.cards[len(table.cards) - 1].value, " - Color: ",table.cards[len(table.cards) - 1].color, "    who: ",table.lastPlacementBy)
        table.lastPlacementBy = playerList[table.turn].id

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
        playerList[table.turn].cards = hand

        # check if color must be changed
        if table.cards[len(table.cards) - 1].color == 4:
            table.cards[len(table.cards) - 1].color = changeColor(playerList,table)
        
        
        return table, playerList, hand

avg_turns = []
def startGame():

    simulation = 0

    # Run the simulation
    while (simulation < NUMBER_OF_SIMULATIONS_PER_THREAD and NUMBER_OF_SIMULATIONS_PER_THREAD != 0) or (NUMBER_OF_SIMULATIONS_PER_THREAD == 0):

        playerList = []
        
        deck = shuffleDeck(generateDeck())
        
        # Determine the order of play (default is clockwise)
        table = Table(deck)
        
        # Place the top card of the draw pile face-up in the middle of the table : table.top_card
        table.cards.append(table.deck.pop(0))

        # Deal 7 cards to each player
        spawnPlayers(deck, playerList)

        # Run the game
        winners = 0
        turns = 0

        # Pickle data
        game_data = {}

        game_data["Simulation_"+str(simulation)] = { 'Turns': {} }

        
        while (ONLY_ONE_PLAYER_CAN_WIN and winners == 0) or (not ONLY_ONE_PLAYER_CAN_WIN and winners < NUMBER_OF_PLAYERS-1):
            
            # failsafe
            if len(table.deck) == 0 and len(table.cards) == 0:
                # Delete current simulation info from data
                game_data["Simulation_"+str(simulation)]["Turns"] = {}
                break

            # check if draw pile is empty
            if len(table.deck) == 0:
                # Shuffle the discard pile and make it the new draw pile
                temp = table.cards.pop(0)
                table.deck = shuffleDeck(table.cards)
                table.cards.append(temp)
            
            
            # if current player has finished, skip turn
            if playerList[table.turn].isAlive == 0:
                table = skipTurn(table, playerList)
                continue
            
            count = 0
            for player in playerList:
                count += player.isAlive

            hand = playerList[table.turn].cards

            #print("-------------------------------- Alive: ",count , " --------- must_be_picked: ",table.to_be_drawn)

            # handle skip turn
            while(table.turns_to_be_skipped > 0 and table.lastPlacementBy != table.turn):
                table.turns_to_be_skipped += -1
                table = skipTurn(table, playerList) # end turn

            # Player's turn starts here
            turns += 1

            turn_data = {
                "player_id": table.turn,
                "player_cards_begin_turn": [vars(card) for card in playerList[table.turn].cards],
                "player_cards_used": [],
                "player_cards_end_turn": [],
                "player_drew_amount": 0
            }
            # IF the current player has a playable card:
            if canPlayerPlay(hand, table, playerList):
                
                table, playerList, hand = logic(table, playerList, hand)
                
                hand_data = [vars(card) for card in hand]
                hold_tuples = [tuple(d.items()) for d in turn_data["player_cards_begin_turn"]]
                hand_tuples = [tuple(d.items()) for d in hand_data]

                # Find removed elements (present in hold_arr but not in hand_diff)
                removed = [dict(t) for t in set(hold_tuples) - set(hand_tuples)]
                turn_data["player_cards_used"].append(removed)


            else:
                # Draw

                # If the player can't respond to a draw card, then this will handle Draw +2, +4, +10, ... very well
                draw_amount = 1
                if table.to_be_drawn > 0:
                    draw_amount = table.to_be_drawn
                    table.to_be_drawn = 0

                turn_data["player_drew_amount"] = draw_amount
                drawn = drawCards(table.deck, draw_amount, table.turn)
                for card in drawn:
                    hand.append(card)

                playerList[table.turn].cards = hand
                
                # IF the drawn card is playable:
                if canPlayerPlay(hand, table, playerList):
                    table, playerList, hand = logic(table, playerList, hand)

                    
                    hand_data = [vars(card) for card in hand]
                    hold_tuples = [tuple(d.items()) for d in turn_data["player_cards_begin_turn"]]
                    hand_tuples = [tuple(d.items()) for d in hand_data]

                    # Find removed elements (present in hold_arr but not in hand_diff)
                    removed = [dict(t) for t in set(hold_tuples) - set(hand_tuples)]
                    turn_data["player_cards_used"].append(removed)


            # handle Reverses
            while (table.reverses > 0 and table.lastPlacementBy != table.turn):
                table.direction = not table.direction
                table.reverses += -1

            # IF a player has no cards left:
            if (len(playerList[table.turn].cards) == 0):
                # Game over
                # Player with no cards left wins
                points = 0
                for player in playerList:
                    if player != playerList[table.turn]:
                        for card in player.cards:
                            points += card.points
                
                winners += 1
                playerList[table.turn].points = points
                playerList[table.turn].isAlive = 0
                #print("Winner: ", winners)
                

            table = skipTurn(table, playerList) # end turn

            # store turn data
            turn_data["player_cards_end_turn"] = [vars(card) for card in playerList[table.turn].cards]
            game_data["Simulation_"+str(simulation)]["Turns"][turns] = turn_data

        avg_turns.append(turns)

        if NUMBER_OF_SIMULATIONS_PER_THREAD > 0:
            simulation += 1

    # Store all game data into file
    with open("data.pickle", "wb") as file:
        # Write the data to the file
        pickle.dump(game_data, file)

# implement threads
startGame()


print("Avg turns: ",np.mean(avg_turns), " - Minutes: ",np.mean(avg_turns) * 2 / 60)



"""
Things done so far:
    create shuffled deck
    spawn players
    give each player 7 cards
    implement canPlay logic

    implement game_data in pickle format
"""