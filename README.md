# GDINTAI SokoBot

**Author:** Rhyss Damien Medina\
**Contributor:** Patricia Naui\
**Language:** Python

## Overview
This project is an implementation of the Sokoban solver 'SokoBot' using the A* search algorithm.

## How to Run the Sokobot GUI
To view the Sokobot solving a level in real time:\

1. On the terminal, input `./sokobot.sh [map-name] --gui` (for example, `./sokobot.sh 20 --gui`).

## How to Run the Sokobot Solver for Benchmarking
`test_solver.py` is a script to identify the performance of `solveSokobanPuzzle` across all the maps provided in the maps/ folder.\

1. On the terminal, input `python sokobot.py` or `python3 sokobot.py` for Mac.
2. On a separate terminal window, input `python test_solver.py` or `python3 test_solver.py` for Mac.