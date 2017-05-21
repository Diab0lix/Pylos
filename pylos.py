#!/usr/bin/env python3
# pylos.py
# Author: Quentin Lurkin, Thierry Frycia
# Version: May 21, 2017
# -*- coding: utf-8 -*-

import argparse
import socket
import sys
import json
import copy

from lib import game

class PylosState(game.GameState):
    '''Class representing a state for the Pylos game.'''
    def __init__(self, initialstate=None):
        
        if initialstate == None:
            # define a layer of the board
            def squareMatrix(size):
                matrix = []
                for i in range(size):
                    matrix.append([None]*size)
                return matrix

            board = []
            for i in range(4):
                board.append(squareMatrix(4-i))

            initialstate = {
                'board': board,
                'reserve': [15, 15],
                'turn': 0
            }

        super().__init__(initialstate)
    
    def state(self):
        return self._state['visible']

    def get(self, layer, row, column):
        if layer < 0 or row < 0 or column < 0:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))         
        try:
            return self._state['visible']['board'][layer][row][column]
        except:
            raise game.InvalidMoveException('The position ({}) is outside of the board'.format([layer, row, column]))

    def safeGet(self, layer, row, column):
        try:
            return self.get(layer, row, column)
        except game.InvalidMoveException:
            return None

    def validPosition(self, layer, row, column):
        if self.get(layer, row, column) != None:
            raise game.InvalidMoveException('The position ({}) is not free'.format([layer, row, column]))

        if layer > 0:
            if (
                self.get(layer-1, row, column) == None or
                self.get(layer-1, row+1, column) == None or
                self.get(layer-1, row+1, column+1) == None or
                self.get(layer-1, row, column+1) == None
            ):
                raise game.InvalidMoveException('The position ({}) is not stable'.format([layer, row, column]))

    def canMove(self, layer, row, column):
        if self.get(layer, row, column) == None:
            raise game.InvalidMoveException('The position ({}) is empty'.format([layer, row, column]))

        if layer < 3:
            if (
                self.safeGet(layer+1, row, column) != None or
                self.safeGet(layer+1, row-1, column) != None or
                self.safeGet(layer+1, row-1, column-1) != None or
                self.safeGet(layer+1, row, column-1) != None
            ):
                raise game.InvalidMoveException('The position ({}) is not movable'.format([layer, row, column]))

    def createSquare(self, coord):
        layer, row, column = tuple(coord)

        def isSquare(layer, row, column):
            if (
                self.safeGet(layer, row, column) != None and
                self.safeGet(layer, row+1, column) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row+1, column+1) == self.safeGet(layer, row, column) and
                self.safeGet(layer, row, column+1) == self.safeGet(layer, row, column)
            ):
                return True
            return False

        if (
            isSquare(layer, row, column) or
            isSquare(layer, row-1, column) or
            isSquare(layer, row-1, column-1) or
            isSquare(layer, row, column-1)
        ):
            return True
        return False

    def set(self, coord, value):
        layer, row, column = tuple(coord)
        self.validPosition(layer, row, column)
        self._state['visible']['board'][layer][row][column] = value

    def remove(self, coord, player):
        layer, row, column = tuple(coord)
        self.canMove(layer, row, column)
        sphere = self.get(layer, row, column)
        if sphere != player:
            raise game.InvalidMoveException('not your sphere')
        self._state['visible']['board'][layer][row][column] = None
        
    # update the state with the move
    # raise game.InvalidMoveException
    def update(self, move, player):
        state = self._state['visible']
        if move['move'] == 'place':
            if state['reserve'][player] < 1:
                raise game.InvalidMoveException('no more spheres')
            self.set(move['to'], player)
            state['reserve'][player] -= 1
        elif move['move'] == 'move':
            if move['to'][0] <= move['from'][0]:
                raise game.InvalidMoveException('you can only move to upper layer')
            sphere = self.remove(move['from'], player)
            try:
                self.set(move['to'], player)
            except game.InvalidMoveException as e:
                self.set(move['from'], player) 
                raise e
        else:
            raise game.InvalidMoveException('Invalid Move:\n{}'.format(move))

        if 'remove' in move:
            if not self.createSquare(move['to']):
                raise game.InvalidMoveException('You cannot remove spheres')
            if len(move['remove']) > 2:
                raise game.InvalidMoveException('Can\'t remove more than 2 spheres')
            for coord in move['remove']:
                sphere = self.remove(coord, player)
                state['reserve'][player] += 1

        state['turn'] = (state['turn'] + 1) % 2


    # return 0 or 1 if a winner, return None if draw, return -1 if game continue
    def winner(self):
        state = self._state['visible']
        if state['reserve'][0] < 1:
            return 1
        elif state['reserve'][1] < 1:
            return 0
        return -1

    def val2str(self, val):
        return '_' if val == None else '@' if val == 0 else 'O'

    def player2str(self, val):
        return 'Light' if val == 0 else 'Dark'

    def printSquare(self, matrix):
        print(' ' + '_'*(len(matrix)*2-1))
        print('\n'.join(map(lambda row : '|' + '|'.join(map(self.val2str, row)) + '|', matrix)))

    # print the state
    def prettyprint(self):
        state = self._state['visible']
        for layer in range(4):
            self.printSquare(state['board'][layer])
            print()
        
        for player, reserve in enumerate(state['reserve']):
            print('Reserve of {}:'.format(self.player2str(player)))
            print((self.val2str(player)+' ')*reserve)
            print()
        
        print('{} to play !'.format(self.player2str(state['turn'])))
        #print(json.dumps(self._state['visible'], indent=4))       

class PylosServer(game.GameServer):
    '''Class representing a server for the Pylos game.'''
    def __init__(self, verbose=False):
        super().__init__('Pylos', 2, PylosState(), verbose=verbose)
    
    def applymove(self, move):
        try:
            self._state.update(json.loads(move), self.currentplayer)
        except json.JSONDecodeError:
            raise game.InvalidMoveException('move must be valid JSON string: {}'.format(move))


class PylosClient(game.GameClient):
    '''Class representing a client for the Pylos game.'''
    def __init__(self, name, server, verbose=False):
        super().__init__(server, PylosState, verbose=verbose)
        self.__name = name
    
    def _handle(self, message):
        pass
    
    # Return move as string
    def _nextmove(self, state):
        player = state.state()['turn']
        bestScore, bestMove = minimax(state, player)
        return json.dumps(bestMove)

# Recursive minimax function
# Searches the tree depth-first and returns the best move for a given player to the parent
def minimax(state, player, depth=3):
    bestScore = None
    bestMove = None
    for move in options(state):
        newState = copy.deepcopy(state)
        nextState = applyMove(newState, move) 
        if depth > 0:
            # Call itself again, but one level deeper and play as opponent
            playedScore, playedMove = minimax(nextState, 1-player, depth-1)

            # Means we've reached the end of the game and we don't have any balls left
            # We don't want to continue, so just try the next move in the list
            if playedMove == None:
                bestMove = move
                bestScore = evaluate(bestMove, player)
                continue
        else:
            # Reached the last level -> evaluate the score and pass it to parent
            playedScore = evaluate(nextState, player)
            playedMove = move
        
        # First time in the for loop
        if bestScore == None:
            bestScore = playedScore
            bestMove = move

        # Maximize the score
        if playedScore > bestScore:
            bestScore = playedScore
            bestMove = move

    # Each player tries to maximize the score
    # A good score for my opponent means a bad score for me
    # That's why we return -bestScore
    return (-bestScore, bestMove) 
    
# Give the score of the game
# Just look at the difference between the number of balls in each player's reserve
# If my opponent has more balls than me, that's bad and score will be negative
def evaluate(state, player):
    return state.state()['reserve'][player] - state.state()['reserve'][1-player]

# Simulates a move applied to a state without changing the original state and making the game progress
def applyMove(stateOrig, move):
    state = copy.deepcopy(stateOrig)
    player = state.state()['turn']
    try:
        state.update(move, player)
    except:
        print(state.state())
        print(move)
    return state

# Returns all possible moves possible for one player depending on the state
def options(state_):
    state = copy.deepcopy(state_)
    emptySpots = []
    canMove = []
    possibleMoves = []

    for layer in range(len(state.state()['board'])):
        for row in range(len(state.state()['board'][layer])):
            for column in range(len(state.state()['board'][layer][row])):
                if state.state()['board'][layer][row][column] == None:
                    # Make a list of empty places where a ball can be placed on
                    try:
                        state.validPosition(layer, row, column)
                        emptySpots.append([layer, row, column])
                    except:
                        pass
                if state.state()['board'][layer][row][column] == state.state()['turn']:
                    # Make a list of the balls that don't support anything and can be (re)moved
                    try:
                        state.canMove(layer, row, column)
                        canMove.append([layer, row, column])
                    except:
                        pass

    for layer in range(len(state.state()['board'])):
        for row in range(len(state.state()['board'][layer])):
            for column in range(len(state.state()['board'][layer][row])):                 
                # Make a square of own color if 3 are already in a corner
                for i in ((1,1),(1,-1),(-1,1),(-1,-1)): # Maybe there's a better way by using state.createSquare()
                    try:
                        if state.state()['board'][layer][row][column] == state.state()['board'][layer][row+i[0]][column] == state.state()['board'][layer][row][column+i[1]] != None and [layer,row+i[0],column+i[1]] in emptySpots and state.state()['reserve'][state.state()['turn']] > 0: # any ideas to make it even longer?
                            if state.state()['board'][layer][row][column] == state.state()['turn']:
                                for j in canMove:
                                    possibleMoves.append({
                                                'move': 'place',
                                                'to': [layer,row+i[0],column+i[1]],
                                                'remove': [
                                                    [layer,row+i[0],column+i[1]],
                                                    j
                                                ]})
                            else:
                                possibleMoves.append({
                                            'move': 'place',
                                            'to': [layer,row+i[0],column+i[1]]
                                            })
                    except IndexError:
                        pass
    
    # Make a list of bells that can be moved up
    for move in canMove:
        for spot in emptySpots:
            if move[0] < spot[0]:
                if spot[1]-move[1] > 0 or spot[2]-move[2] > 0:
                    possibleMoves.append({
                               'move': 'move',
                               'from': move,
                               'to': spot
                           })
   
    # Place a ball from the reseve in each possible spot
    if state.state()['reserve'][state.state()['turn']] > 0:
        for i in emptySpots:
            possibleMoves.append({
            'move': 'place',
            'to': i
        })

    return possibleMoves

if __name__ == '__main__':
    # Create the top-level parser
    parser = argparse.ArgumentParser(description='Pylos game')
    subparsers = parser.add_subparsers(description='server client', help='Pylos game components', dest='component')
    # Create the parser for the 'server' subcommand
    server_parser = subparsers.add_parser('server', help='launch a server')
    server_parser.add_argument('--host', help='hostname (default: localhost)', default='localhost')
    server_parser.add_argument('--port', help='port to listen on (default: 5000)', default=5000)
    server_parser.add_argument('--verbose', action='store_true')
    # Create the parser for the 'client' subcommand
    client_parser = subparsers.add_parser('client', help='launch a client')
    client_parser.add_argument('name', help='name of the player')
    client_parser.add_argument('--host', help='hostname of the server (default: localhost)', default='127.0.0.1')
    client_parser.add_argument('--port', help='port of the server (default: 5000)', default=5000)
    client_parser.add_argument('--verbose', action='store_true')
    # Parse the arguments of sys.args
    args = parser.parse_args()
    if args.component == 'server':
        PylosServer(verbose=args.verbose).run()
    else:
        PylosClient(args.name, (args.host, args.port), verbose=args.verbose)
