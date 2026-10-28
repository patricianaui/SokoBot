import time
import os
import sys
import re

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.reader.file_reader import FileReader
from src.solver.sokobot import SokoBot


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def split_map(map_data):
    static_map = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]
    items = [[" " for _ in range(map_data.columns)] for _ in range(map_data.rows)]

    for row in range(map_data.rows):
        for column in range(map_data.columns):
            tile = map_data.tiles[row][column]
            if tile == "#":
                static_map[row][column] = "#"
            elif tile == "@":
                items[row][column] = "@"
            elif tile == "$":
                items[row][column] = "$"
            elif tile == ".":
                static_map[row][column] = "."
            elif tile == "+":
                static_map[row][column] = "."
                items[row][column] = "@"
            elif tile == "*":
                static_map[row][column] = "."
                items[row][column] = "$"

    return static_map, items


def validate_solution(static_map, items, width, height, solution):
    board = [row[:] for row in items]

    player_row = -1
    player_col = -1
    for r in range(height):
        for c in range(width):
            if board[r][c] == '@':
                player_row = r
                player_col = c

    if player_row == -1:
        return False, "No player found on the board"

    direction_map = {
        'u': (-1, 0),
        'd': (1, 0),
        'l': (0, -1),
        'r': (0, 1),
    }

    for i, move in enumerate(solution):
        if move not in direction_map:
            return False, f"Move {i}: Invalid character '{move}'"

        dr, dc = direction_map[move]
        next_r = player_row + dr
        next_c = player_col + dc

        if next_r < 0 or next_r >= height or next_c < 0 or next_c >= width:
            return False, f"Move {i} ('{move}'): Out of bounds"

        if static_map[next_r][next_c] == '#':
            return False, f"Move {i} ('{move}'): Wall collision at ({next_r},{next_c})"

        if board[next_r][next_c] == '$':
            box_r = next_r + dr
            box_c = next_c + dc

            if box_r < 0 or box_r >= height or box_c < 0 or box_c >= width:
                return False, f"Move {i} ('{move}'): Crate pushed out of bounds"

            if static_map[box_r][box_c] == '#':
                return False, f"Move {i} ('{move}'): Crate pushed into wall at ({box_r},{box_c})"

            if board[box_r][box_c] == '$':
                return False, f"Move {i} ('{move}'): Crate pushed into another crate at ({box_r},{box_c})"

            board[box_r][box_c] = '$'
            board[next_r][next_c] = '@'
            board[player_row][player_col] = ' '
            player_row = next_r
            player_col = next_c

        else:
            board[next_r][next_c] = '@'
            board[player_row][player_col] = ' '
            player_row = next_r
            player_col = next_c

    for r in range(height):
        for c in range(width):
            if static_map[r][c] == '.' and board[r][c] != '$':
                return False, f"Target at ({r},{c}) not covered by a crate"

    return True, "All targets covered — VALID solution"


def count_crates(items):
    count = 0
    for row in items:
        for cell in row:
            if cell == '$':
                count += 1
    return count


def main():
    file_reader = FileReader()

    maps_dir = os.path.join(project_root, "maps")

    if not os.path.exists(maps_dir):
        print(f"Error: Maps directory not found at '{maps_dir}'")
        return

    map_files = [f for f in os.listdir(maps_dir) if not f.startswith('.')]

    map_files.sort(key=natural_sort_key)

    print("=" * 85)
    print(f"{'Map':<14} {'Crates':<7} {'Status':<10} {'Moves':<8} {'Time (s)':<10} {'Validation'}")
    print("=" * 85)

    total = 0
    passed = 0

    for filename in map_files:
        map_name, _ = os.path.splitext(filename)

        map_data = file_reader.read_file(map_name)
        if map_data is None:
            map_data = file_reader.read_file(filename)

        if map_data is None:
            print(f"{map_name:<14} {'?':<7} {'NO FILE':<10}")
            continue

        static_map, items = split_map(map_data)
        crates = count_crates(items)

        total += 1
        bot = SokoBot()

        start = time.perf_counter() 
        solution = bot.solveSokobanPuzzle(map_data.columns, map_data.rows, static_map, items)
        elapsed = time.perf_counter() - start

        if solution == "" or solution is None:
            status = "EMPTY"
            move_count = 0
            validation = "No solution returned"
        else:
            status = "SOLVED"
            move_count = len(solution)
            static_map2, items2 = split_map(map_data)
            valid, msg = validate_solution(static_map2, items2, map_data.columns, map_data.rows, solution)
            if valid:
                validation = "PASS"
                passed += 1
            else:
                validation = f"FAIL: {msg}"

        print(f"{map_name:<14} {crates:<7} {status:<10} {move_count:<8} {elapsed:<10.4f} {validation}")

    print("=" * 85)
    print(f"Results: {passed}/{total} maps solved and validated")
    print()


if __name__ == "__main__":
    main()