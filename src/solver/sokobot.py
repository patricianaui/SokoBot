import time
import heapq
from collections import deque


# Direction Constants

DIRECTIONS = [
    ('u', -1, 0),   # Up
    ('d', 1, 0),    # Down
    ('l', 0, -1),   # Left
    ('r', 0, 1),    # Right
]


# State Extraction Functions

def find_player_position(items_data, width, height):
    for row in range(height):
        for col in range(width):
            if items_data[row][col] == '@':
                return (row, col)
    return None


def find_crate_positions(items_data, width, height):
    crates = []
    for row in range(height):
        for col in range(width):
            if items_data[row][col] == '$':
                crates.append((row, col))
    crates.sort()
    return tuple(crates)


def find_target_positions(map_data, width, height):
    targets = set()
    for row in range(height):
        for col in range(width):
            if map_data[row][col] == '.':
                targets.add((row, col))
    return frozenset(targets)



# Deadlock Detection

def find_dead_squares(map_data, targets, width, height):
    dead = set()

    for r in range(height):
        for c in range(width):
            if map_data[r][c] == '#' or (r, c) in targets:
                continue

            wall_up = (r == 0) or (map_data[r - 1][c] == '#')
            wall_down = (r == height - 1) or (map_data[r + 1][c] == '#')
            wall_left = (c == 0) or (map_data[r][c - 1] == '#')
            wall_right = (c == width - 1) or (map_data[r][c + 1] == '#')

            if (wall_up or wall_down) and (wall_left or wall_right):
                dead.add((r, c))

    for r in range(height):
        corners_in_row = []
        for c in range(width):
            if (r, c) in dead:
                corners_in_row.append(c)

        for i in range(len(corners_in_row)):
            for j in range(i + 1, len(corners_in_row)):
                c1 = corners_in_row[i]
                c2 = corners_in_row[j]

                has_wall = False
                for c in range(c1 + 1, c2):
                    if map_data[r][c] == '#':
                        has_wall = True
                        break
                if has_wall:
                    continue

                has_target = False
                for c in range(c1 + 1, c2):
                    if (r, c) in targets:
                        has_target = True
                        break
                if has_target:
                    continue

                wall_above = True
                for c in range(c1, c2 + 1):
                    if r > 0 and map_data[r - 1][c] != '#':
                        wall_above = False
                        break

                wall_below = True
                if not wall_above:
                    for c in range(c1, c2 + 1):
                        if r < height - 1 and map_data[r + 1][c] != '#':
                            wall_below = False
                            break

                if wall_above or wall_below:
                    for c in range(c1 + 1, c2):
                        dead.add((r, c))

    for c in range(width):
        corners_in_col = []
        for r in range(height):
            if (r, c) in dead:
                corners_in_col.append(r)

        for i in range(len(corners_in_col)):
            for j in range(i + 1, len(corners_in_col)):
                r1 = corners_in_col[i]
                r2 = corners_in_col[j]

                has_wall = False
                for r in range(r1 + 1, r2):
                    if map_data[r][c] == '#':
                        has_wall = True
                        break
                if has_wall:
                    continue

                has_target = False
                for r in range(r1 + 1, r2):
                    if (r, c) in targets:
                        has_target = True
                        break
                if has_target:
                    continue

                wall_left = True
                for r in range(r1, r2 + 1):
                    if c > 0 and map_data[r][c - 1] != '#':
                        wall_left = False
                        break

                wall_right = True
                if not wall_left:
                    for r in range(r1, r2 + 1):
                        if c < width - 1 and map_data[r][c + 1] != '#':
                            wall_right = False
                            break

                if wall_left or wall_right:
                    for r in range(r1 + 1, r2):
                        dead.add((r, c))

    return dead


# Dynamic Deadlock Detection

def is_deadlocked(crate_positions, crate_set, targets, map_data, width, height):
    for crate_row, crate_col in crate_positions:
        if crate_row + 1 < height and crate_col + 1 < width:
            cells = [
                (crate_row, crate_col),
                (crate_row, crate_col + 1),
                (crate_row + 1, crate_col),
                (crate_row + 1, crate_col + 1),
            ]

            all_blocked = True
            any_crate_off_target = False

            for r, c in cells:
                is_wall = (map_data[r][c] == '#')
                is_crate = ((r, c) in crate_set)

                if not is_wall and not is_crate:
                    all_blocked = False
                    break

                if is_crate and (r, c) not in targets:
                    any_crate_off_target = True

            if all_blocked and any_crate_off_target:
                return True

    frozen = set()
    changed = True

    while changed:
        changed = False
        for crate_row, crate_col in crate_positions:
            if (crate_row, crate_col) in frozen:
                continue

            left_blocked = (
                crate_col == 0
                or map_data[crate_row][crate_col - 1] == '#'
                or (crate_row, crate_col - 1) in frozen
            )
            right_blocked = (
                crate_col == width - 1
                or map_data[crate_row][crate_col + 1] == '#'
                or (crate_row, crate_col + 1) in frozen
            )

            up_blocked = (
                crate_row == 0
                or map_data[crate_row - 1][crate_col] == '#'
                or (crate_row - 1, crate_col) in frozen
            )
            down_blocked = (
                crate_row == height - 1
                or map_data[crate_row + 1][crate_col] == '#'
                or (crate_row + 1, crate_col) in frozen
            )

            h_blocked = left_blocked or right_blocked
            v_blocked = up_blocked or down_blocked

            if h_blocked and v_blocked:
                frozen.add((crate_row, crate_col))
                changed = True

    for crate in frozen:
        if crate not in targets:
            return True

    return False


# Precomputed Pull Distances (BFS from each target)

def compute_pull_distances(map_data, targets, width, height):
    pull_dist = {}

    for target in targets:
        dist = {}
        dist[target] = 0
        queue = deque()
        queue.append(target)

        while queue:
            r, c = queue.popleft()
            current_d = dist[(r, c)]

            for _, dr, dc in DIRECTIONS:
                prev_r = r + dr
                prev_c = c + dc
                puller_r = r + 2 * dr
                puller_c = c + 2 * dc

                if prev_r < 0 or prev_r >= height or prev_c < 0 or prev_c >= width:
                    continue
                if puller_r < 0 or puller_r >= height or puller_c < 0 or puller_c >= width:
                    continue
                if map_data[prev_r][prev_c] == '#':
                    continue
                if map_data[puller_r][puller_c] == '#':
                    continue

                if (prev_r, prev_c) not in dist:
                    dist[(prev_r, prev_c)] = current_d + 1
                    queue.append((prev_r, prev_c))

        pull_dist[target] = dist

    return pull_dist


# Heuristic Function (using pull distances)

def calculate_heuristic(crate_positions, target_list, cache, pull_dist):
    if crate_positions in cache:
        return cache[crate_positions]

    num_crates = len(crate_positions)
    num_targets = len(target_list)

    if num_crates == 0:
        cache[crate_positions] = 0
        return 0

    if num_targets == 0 or num_crates > num_targets:
        cache[crate_positions] = float('inf')
        return float('inf')

    INF = float('inf')

    dist = []
    for crate_pos in crate_positions:
        row_dists = []
        for target in target_list:
            target_dists = pull_dist.get(target)
            if target_dists is not None and crate_pos in target_dists:
                d = target_dists[crate_pos]
            else:
                d = INF  
            row_dists.append(d)
        dist.append(row_dists)

    size = 1 << num_targets
    dp = [INF] * size
    dp[0] = 0 

    for mask in range(size):
        if dp[mask] == INF:
            continue

        crate_index = bin(mask).count('1')
        if crate_index >= num_crates:
            continue

        for target_index in range(num_targets):
            if mask & (1 << target_index):
                continue 

            d = dist[crate_index][target_index]
            if d == INF:
                continue

            new_mask = mask | (1 << target_index)
            new_cost = dp[mask] + d

            if new_cost < dp[new_mask]:
                dp[new_mask] = new_cost

    result = INF
    for mask in range(size):
        if bin(mask).count('1') == num_crates:
            if dp[mask] < result:
                result = dp[mask]

    cache[crate_positions] = result
    return result


# Flood Fill

def get_reachable_area(player_pos, crate_set, map_data, width, height):
    queue = deque()
    queue.append(player_pos)
    reachable = set()
    reachable.add(player_pos)
    normalized = player_pos

    while queue:
        r, c = queue.popleft()
        if (r, c) < normalized:
            normalized = (r, c)

        for _, dr, dc in DIRECTIONS:
            nr = r + dr
            nc = c + dc
            if 0 <= nr < height and 0 <= nc < width:
                if (nr, nc) not in reachable:
                    if map_data[nr][nc] != '#' and (nr, nc) not in crate_set:
                        reachable.add((nr, nc))
                        queue.append((nr, nc))

    return reachable, normalized


# Goal Check

def is_goal_state(crate_positions, targets):
    for crate in crate_positions:
        if crate not in targets:
            return False
    return True


# Tunnel Detection


def is_tunnel(r, c, dr, dc, map_data, width, height, targets):
    if (r, c) in targets:
        return None 

    pushes = 0
    cr, cc = r, c

    while True:
        if dr != 0:
            left_wall = (cc == 0) or (map_data[cr][cc - 1] == '#')
            right_wall = (cc == width - 1) or (map_data[cr][cc + 1] == '#')
            if not (left_wall and right_wall):
                break  
        else:
            up_wall = (cr == 0) or (map_data[cr - 1][cc] == '#')
            down_wall = (cr == height - 1) or (map_data[cr + 1][cc] == '#')
            if not (up_wall and down_wall):
                break  

        next_r = cr + dr
        next_c = cc + dc

        if next_r < 0 or next_r >= height or next_c < 0 or next_c >= width:
            break
        if map_data[next_r][next_c] == '#':
            break

        if (next_r, next_c) in targets:
            pushes += 1
            cr = next_r
            cc = next_c
            break

        pushes += 1
        cr = next_r
        cc = next_c

    if pushes <= 0:
        return None

    return (cr, cc, pushes)


# Push Finder

def find_all_pushes(reachable, crate_positions, crate_set, map_data,
                    width, height, dead_squares, targets):
    pushes = []

    for crate_row, crate_col in crate_positions:
        for move_char, dr, dc in DIRECTIONS:
            player_row = crate_row - dr
            player_col = crate_col - dc

            if (player_row, player_col) not in reachable:
                continue

            dest_row = crate_row + dr
            dest_col = crate_col + dc

            if dest_row < 0 or dest_row >= height:
                continue
            if dest_col < 0 or dest_col >= width:
                continue

            if map_data[dest_row][dest_col] == '#':
                continue

            dest = (dest_row, dest_col)

            if dest in crate_set:
                continue

            if dest in dead_squares:
                continue

            new_crates = []
            for crate in crate_positions:
                if crate == (crate_row, crate_col):
                    new_crates.append(dest)
                else:
                    new_crates.append(crate)
            new_crates.sort()
            new_crate_tuple = tuple(new_crates)

            new_player = (crate_row, crate_col)
            pushes.append((move_char, new_player, new_crate_tuple, 1))

            tunnel_result = is_tunnel(dest_row, dest_col, dr, dc,
                                      map_data, width, height, targets)
            if tunnel_result is not None:
                tunnel_end_r, tunnel_end_c, tunnel_pushes = tunnel_result
                tunnel_end = (tunnel_end_r, tunnel_end_c)

                if tunnel_end != dest and tunnel_end not in crate_set and tunnel_end not in dead_squares:
                    path_clear = True
                    check_r, check_c = dest_row + dr, dest_col + dc
                    while (check_r, check_c) != tunnel_end:
                        if (check_r, check_c) in crate_set:
                            path_clear = False
                            break
                        check_r += dr
                        check_c += dc

                    if path_clear:
                        tunnel_crates = []
                        for crate in crate_positions:
                            if crate == (crate_row, crate_col):
                                tunnel_crates.append(tunnel_end)
                            else:
                                tunnel_crates.append(crate)
                        tunnel_crates.sort()
                        tunnel_crate_tuple = tuple(tunnel_crates)

                        tunnel_player = (tunnel_end[0] - dr, tunnel_end[1] - dc)
                        total_pushes = 1 + tunnel_pushes
                        pushes.append((move_char, tunnel_player, tunnel_crate_tuple, total_pushes))

    return pushes


# Path Finding

def find_walk_path(start, end, crate_set, map_data, width, height):
    if start == end:
        return ""

    queue = deque()
    queue.append((start, ""))
    visited = set()
    visited.add(start)

    while queue:
        (r, c), path = queue.popleft()

        for move_char, dr, dc in DIRECTIONS:
            nr = r + dr
            nc = c + dc

            if 0 <= nr < height and 0 <= nc < width:
                if (nr, nc) not in visited:
                    if map_data[nr][nc] != '#' and (nr, nc) not in crate_set:
                        new_path = path + move_char
                        if (nr, nc) == end:
                            return new_path
                        visited.add((nr, nc))
                        queue.append(((nr, nc), new_path))

    return None 


# Solution Reconstruction


def reconstruct_full_path(came_from, goal_state, map_data, width, height):
    transitions = []
    current = goal_state
    while current in came_from:
        parent_state, push_char, push_count = came_from[current]
        transitions.append((parent_state, current, push_char, push_count))
        current = parent_state

    transitions.reverse()

    direction_map = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}

    full_moves = []
    for parent_state, child_state, push_char, push_count in transitions:
        parent_player, parent_crates = parent_state
        child_player, child_crates = child_state

        dr, dc = direction_map[push_char]

        parent_crate_set = set(parent_crates)
        child_crate_set = set(child_crates)

        old_crate = None
        for crate in parent_crates:
            if crate not in child_crate_set:
                old_crate = crate
                break

        if old_crate is None:
            continue

        push_from = (old_crate[0] - dr, old_crate[1] - dc)

        crate_set = set(parent_crates)
        walk_path = find_walk_path(parent_player, push_from, crate_set,
                                   map_data, width, height)

        if walk_path is not None:
            full_moves.append(walk_path)

        for _ in range(push_count):
            full_moves.append(push_char)

    return ''.join(full_moves)


# SokoBot Class

class SokoBot:
    def solveSokobanPuzzle(self, width, height, mapData, itemsData):
        nodesExpanded = 0
        statesGenerated = 0

        start_time = time.time()
        TIME_LIMIT = 14.5 
        TIME_CHECK_INTERVAL = 200  


        player_pos = find_player_position(itemsData, width, height)
        crate_positions = find_crate_positions(itemsData, width, height)
        targets = find_target_positions(mapData, width, height)
        target_list = list(targets)


        if is_goal_state(crate_positions, targets):
            return ""


        dead_squares = find_dead_squares(mapData, targets, width, height)

        pull_dist = compute_pull_distances(mapData, targets, width, height)

        initial_state = (player_pos, crate_positions)

        h_cache = {}
        h_start = calculate_heuristic(crate_positions, target_list, h_cache,
                                       pull_dist)

        if h_start == float('inf'):
            return ""

        counter = 0
        open_list = []
        heapq.heappush(open_list, (h_start, h_start, counter, initial_state))
        counter = counter + 1
        statesGenerated += 1

        g_score = {}
        g_score[initial_state] = 0

        came_from = {}

        closed = set()

        iterations = 0

        while len(open_list) > 0:
            iterations = iterations + 1
            if iterations % TIME_CHECK_INTERVAL == 0:
                elapsed = time.time() - start_time
                if elapsed > TIME_LIMIT:
                    return ""

            f_current, _h_tie, _tie, current_state = heapq.heappop(open_list)

            current_player, current_crates = current_state
            current_g = g_score.get(current_state, None)

            if current_g is None:
                continue
            current_h = calculate_heuristic(current_crates, target_list,
                                             h_cache, pull_dist)
            if f_current > current_g + current_h:
                continue

            crate_set = set(current_crates)
            reachable, norm_player = get_reachable_area(
                current_player, crate_set, mapData, width, height
            )
            norm_key = (norm_player, current_crates)

            if norm_key in closed:
                continue
            closed.add(norm_key)

            nodesExpanded += 1 

            if is_goal_state(current_crates, targets):
                return reconstruct_full_path(
                    came_from, current_state, mapData, width, height
                )

            pushes = find_all_pushes(
                reachable, current_crates, crate_set,
                mapData, width, height, dead_squares, targets
            )

            for push_char, new_player, new_crates, push_count in pushes:
                new_state = (new_player, new_crates)
                new_g = current_g + push_count

                old_g = g_score.get(new_state, float('inf'))
                if new_g < old_g:
                    new_crate_set = set(new_crates)
                    if is_deadlocked(new_crates, new_crate_set, targets,
                                     mapData, width, height):
                        continue 

                    h = calculate_heuristic(new_crates, target_list,
                                             h_cache, pull_dist)

                    if h == float('inf'):
                        continue

                    g_score[new_state] = new_g
                    came_from[new_state] = (current_state, push_char, push_count)

                    f = new_g + h
                    heapq.heappush(open_list, (f, h, counter, new_state))
                    counter = counter + 1
                    statesGenerated += 1

        return ""