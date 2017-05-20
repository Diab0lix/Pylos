# Pylos AI
This project is based on the game library by ECAM-Brussels. 

The aim was to try to conceive an AI that would find the best move to play given a state of game.

# Running the simulation
Three instances of the program need to be launched in order to play: one server and two clients connecting to it.
The server can be launched with the following command:

`python3 pylos.py server --verbose`

This command launches one client:

`python3 pylos.py client alice (--verbose)`

The game will automatically start once two clients are connected to the server.
Be sure to run the server before trying to connect to it with the clients.

Tested with python 3.6.1 
