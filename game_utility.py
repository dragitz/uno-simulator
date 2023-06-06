import config
import random
from trueskill import Rating
#from uno import Card, Player, Table


# Yes it's being defined twice :) I've never dealt with circular imports

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

NUMBER_OF_DECKS = config.NUMBER_OF_DECKS
NUMBER_OF_PLAYERS = config.NUMBER_OF_PLAYERS
NUMBER_OF_INITIAL_CARDS = config.NUMBER_OF_INITIAL_CARDS

NUMBER_OF_THREADS = config.NUMBER_OF_THREADS   # to be implemented
NUMBER_OF_SIMULATIONS_PER_THREAD = config.NUMBER_OF_SIMULATIONS_PER_THREAD  # type 0 to make it endless

PLAYER_ID = config.PLAYER_ID

# Rules
ONLY_ONE_PLAYER_CAN_WIN = config.ONLY_ONE_PLAYER_CAN_WIN

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