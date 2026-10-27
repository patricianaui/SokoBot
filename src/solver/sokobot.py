import time
import heapq
from collections import deque


# ============================================================
# DIRECTION CONSTANTS
# Each entry: (move_character, row_change, col_change)
# ============================================================

DIRECTIONS = [
    ('u', -1, 0),   # Up
    ('d', 1, 0),    # Down
    ('l', 0, -1),   # Left
    ('r', 0, 1),    # Right
]


# ============================================================
# STATE EXTRACTION FUNCTIONS
# ============================================================


def find_player_position(items_data, width, height):
    """
    Scan the items grid to find where the player '@' is located.
    Returns a tuple (row, col).
    """
    for row in range(height):
        for col in range(width):
            if items_data[row][col] == '@':
                return (row, col)
    return None


def find_crate_positions(items_data, width, height):
    """
    Scan the items grid to find all crate '$' positions.
    Returns a sorted tuple of (row, col) pairs.
    Sorting makes the tuple a unique key for state comparison.
    """
    crates = []
    for row in range(height):
        for col in range(width):
            if items_data[row][col] == '$':
                crates.append((row, col))
    crates.sort()
    return tuple(crates)


def find_target_positions(map_data, width, height):
    """
    Scan the static map to find all target '.' positions.
    Returns a frozenset for fast membership checks.
    """
    targets = set()
    for row in range(height):
        for col in range(width):
            if map_data[row][col] == '.':
                targets.add((row, col))
    return frozenset(targets)


# ============================================================
# DEADLOCK DETECTION
# ============================================================


def find_dead_squares(map_data, targets, width, height):
    """
    Find positions where a crate can never reach any target.

    Detects two types of deadlocks:

    1. Corner deadlocks:
       A non-target tile with a wall on one vertical side (up or down)
       AND a wall on one horizontal side (left or right).
       A crate pushed into such a corner is permanently stuck.

    2. Wall-line deadlocks:
       A row or column segment between two corner dead squares where
       there is a continuous wall on one side and no targets in between.
       A crate in this segment can only slide along the wall but can
       never reach a target.
    """
    dead = set()

    # --- Step 1: Find corner dead squares ---

    for r in range(height):
        for c in range(width):
            # Skip walls and target tiles.
            if map_data[r][c] == '#' or (r, c) in targets:
                continue

            wall_up = (r == 0) or (map_data[r - 1][c] == '#')
            wall_down = (r == height - 1) or (map_data[r + 1][c] == '#')
            wall_left = (c == 0) or (map_data[r][c - 1] == '#')
            wall_right = (c == width - 1) or (map_data[r][c + 1] == '#')

            # A corner has a wall on at least one vertical side
            # AND at least one horizontal side.
            if (wall_up or wall_down) and (wall_left or wall_right):
                dead.add((r, c))

    # --- Step 2: Find wall-line dead squares (horizontal) ---
    # For each row, find pairs of corner dead squares and check if
    # the entire segment between them has a continuous wall above
    # or below with no targets.

    for r in range(height):
        # Collect corner dead squares in this row.
        corners_in_row = []
        for c in range(width):
            if (r, c) in dead:
                corners_in_row.append(c)

        for i in range(len(corners_in_row)):
            for j in range(i + 1, len(corners_in_row)):
                c1 = corners_in_row[i]
                c2 = corners_in_row[j]

                # Check that all squares between c1 and c2 are floor.
                has_wall = False
                for c in range(c1 + 1, c2):
                    if map_data[r][c] == '#':
                        has_wall = True
                        break
                if has_wall:
                    continue

                # Check that there are no targets between the corners.
                has_target = False
                for c in range(c1 + 1, c2):
                    if (r, c) in targets:
                        has_target = True
                        break
                if has_target:
                    continue

                # Check for a continuous wall above the entire segment.
                wall_above = True
                for c in range(c1, c2 + 1):
                    if r > 0 and map_data[r - 1][c] != '#':
                        wall_above = False
                        break

                # Check for a continuous wall below the entire segment.
                wall_below = True
                if not wall_above:
                    for c in range(c1, c2 + 1):
                        if r < height - 1 and map_data[r + 1][c] != '#':
                            wall_below = False
                            break

                if wall_above or wall_below:
                    for c in range(c1 + 1, c2):
                        dead.add((r, c))

    # --- Step 3: Find wall-line dead squares (vertical) ---
    # Same logic applied to columns.

    for c in range(width):
        # Collect corner dead squares in this column.
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


# ============================================================
# DYNAMIC DEADLOCK DETECTION
# ============================================================


def is_deadlocked(crate_positions, crate_set, targets, map_data, width, height):
    """
    Check if the current crate configuration is deadlocked.

    Detects two types of dynamic deadlocks:

    1. Freeze deadlock:
       A crate is "frozen" if it has a wall or another frozen crate on
       at least one horizontal side AND at least one vertical side.
       A frozen crate can never be pushed again. If any frozen crate
       is NOT on a target, the puzzle is unsolvable from this state.

    2. 2x2 block deadlock:
       If any 2x2 area contains only walls and crates (all 4 cells
       are filled), and at least one crate in that block is not on
       a target, the puzzle is unsolvable.
    """
    # --- Check 1: 2x2 block deadlock ---
    # Faster to check first since it doesn't require iteration.

    for crate_row, crate_col in crate_positions:
        # Check the 2x2 block with this crate as top-left.
        if crate_row + 1 < height and crate_col + 1 < width:
            # All 4 cells must be wall or crate.
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

    # --- Check 2: Freeze deadlock ---
    # Iteratively find frozen crates. A crate becomes frozen when it has
    # a wall or previously-frozen crate on one horizontal side AND one
    # vertical side, creating an immovable corner.

    frozen = set()
    changed = True

    while changed:
        changed = False
        for crate_row, crate_col in crate_positions:
            if (crate_row, crate_col) in frozen:
                continue

            # Check horizontal sides.
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

            # Check vertical sides.
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

            # Frozen = blocked on at least one horizontal side
            # AND at least one vertical side (forms a corner trap).
            h_blocked = left_blocked or right_blocked
            v_blocked = up_blocked or down_blocked

            if h_blocked and v_blocked:
                frozen.add((crate_row, crate_col))
                changed = True

    # If any frozen crate is NOT on a target, it's a deadlock.
    for crate in frozen:
        if crate not in targets:
            return True

    return False


# ============================================================
# PRECOMPUTED PULL DISTANCES (BFS from each target)
# ============================================================


def compute_pull_distances(map_data, targets, width, height):
    """
    For each target, compute the minimum number of pushes needed to
    push a crate from any floor tile TO that target. This is done by
    simulating the REVERSE: starting from the target and "pulling"
    the crate outward (which is equivalent to pushing it inward).

    In a pull, the crate moves from position (r, c) to
    (r - dr, c - dc) and the "puller" must be at (r + dr, c + dc)
    — both positions must be floor tiles.

    This gives us a distance table that accounts for walls, unlike
    simple Manhattan distance. The result is a tighter (better)
    heuristic for A*.

    Returns a dictionary:
        pull_dist[(target_r, target_c)][(crate_r, crate_c)] = distance
    """
    pull_dist = {}

    for target in targets:
        dist = {}
        dist[target] = 0
        queue = deque()
        queue.append(target)

        while queue:
            r, c = queue.popleft()
            current_d = dist[(r, c)]

            # Try pulling the crate in each direction.
            # To "pull" means the crate was at (r + dr, c + dc) and got
            # pulled to (r, c). The puller was at (r + 2*dr, c + 2*dc).
            for _, dr, dc in DIRECTIONS:
                # Where the crate came from (previous position).
                prev_r = r + dr
                prev_c = c + dc
                # Where the puller must have been standing.
                puller_r = r + 2 * dr
                puller_c = c + 2 * dc

                # Both positions must be inside the board and not walls.
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


# ============================================================
# HEURISTIC FUNCTION (using pull distances)
# ============================================================


def calculate_heuristic(crate_positions, target_list, cache, pull_dist):
    """
    Estimate the minimum remaining pushes using optimal crate-to-target
    assignment with precomputed pull distances.
    """
    # Use cache to avoid recalculating for the same crate layout.
    if crate_positions in cache:
        return cache[crate_positions]

    num_crates = len(crate_positions)
    num_targets = len(target_list)

    # If there are no crates, cost is 0
    if num_crates == 0:
        cache[crate_positions] = 0
        return 0

    # If there are no targets or more crates than targets, puzzle is unsolvable
    if num_targets == 0 or num_crates > num_targets:
        cache[crate_positions] = float('inf')
        return float('inf')

    INF = float('inf')

    # Precompute distance matrix from each crate to each target
    dist = []
    for crate_pos in crate_positions:
        row_dists = []
        for target in target_list:
            target_dists = pull_dist.get(target)
            if target_dists is not None and crate_pos in target_dists:
                d = target_dists[crate_pos]
            else:
                d = INF  # Crate cannot reach this target
            row_dists.append(d)
        dist.append(row_dists)

    # Bitmask DP over available targets
    size = 1 << num_targets
    dp = [INF] * size
    dp[0] = 0  # 0 targets assigned, cost = 0

    for mask in range(size):
        if dp[mask] == INF:
            continue

        # Number of set bits indicates which crate index to assign next
        crate_index = bin(mask).count('1')
        if crate_index >= num_crates:
            continue

        # Try assigning this crate to each unassigned target
        for target_index in range(num_targets):
            if mask & (1 << target_index):
                continue  # Target already used

            d = dist[crate_index][target_index]
            if d == INF:
                continue

            new_mask = mask | (1 << target_index)
            new_cost = dp[mask] + d

            if new_cost < dp[new_mask]:
                dp[new_mask] = new_cost

    # Find the minimum cost across all masks that assigned all crates
    result = INF
    for mask in range(size):
        if bin(mask).count('1') == num_crates:
            if dp[mask] < result:
                result = dp[mask]

    cache[crate_positions] = result
    return result


# ============================================================
# REACHABILITY (Flood Fill)
# ============================================================


def get_reachable_area(player_pos, crate_set, map_data, width, height):
    """
    Find all tiles the player can walk to from their current position
    without crossing walls or crates. Uses BFS (flood fill).

    Returns:
        reachable: a set of all reachable (row, col) positions
        normalized: the smallest (row, col) in the reachable area,
                    used as a canonical label for this connected region
    """
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


# ============================================================
# GOAL CHECK
# ============================================================


def is_goal_state(crate_positions, targets):
    """Check if every crate is sitting on a target tile."""
    for crate in crate_positions:
        if crate not in targets:
            return False
    return True


# ============================================================
# TUNNEL DETECTION
# ============================================================


def is_tunnel(r, c, dr, dc, map_data, width, height, targets):
    """
    Check if position (r, c) is inside a "tunnel" when a crate is
    being pushed in direction (dr, dc).

    A tunnel is a 1-wide corridor where the crate can only continue
    forward or go back — there are no side openings. When a crate
    enters a tunnel that has no targets inside, we can skip straight
    to the end of the tunnel, since stopping in the middle produces
    no new push opportunities.

    Returns the final position and number of pushes if it's a tunnel,
    or None if it's not a tunnel.
    """
    # Only check for tunnels along straight corridors.
    # For a horizontal push (dc != 0), check walls above and below.
    # For a vertical push (dr != 0), check walls left and right.

    if (r, c) in targets:
        return None  # Don't skip targets.

    pushes = 0
    cr, cc = r, c

    while True:
        # Check if this position has walls on both perpendicular sides.
        if dr != 0:
            # Vertical push — check left and right walls.
            left_wall = (cc == 0) or (map_data[cr][cc - 1] == '#')
            right_wall = (cc == width - 1) or (map_data[cr][cc + 1] == '#')
            if not (left_wall and right_wall):
                break  # Not a tunnel anymore — there's a side opening.
        else:
            # Horizontal push — check up and down walls.
            up_wall = (cr == 0) or (map_data[cr - 1][cc] == '#')
            down_wall = (cr == height - 1) or (map_data[cr + 1][cc] == '#')
            if not (up_wall and down_wall):
                break  # Not a tunnel anymore.

        # Try to continue pushing forward.
        next_r = cr + dr
        next_c = cc + dc

        # Check if next position is valid (inside board and not a wall).
        if next_r < 0 or next_r >= height or next_c < 0 or next_c >= width:
            break
        if map_data[next_r][next_c] == '#':
            break

        # Check if the next position is a target — stop here.
        if (next_r, next_c) in targets:
            pushes += 1
            cr = next_r
            cc = next_c
            break

        # Continue through the tunnel.
        pushes += 1
        cr = next_r
        cc = next_c

    if pushes <= 0:
        return None

    return (cr, cc, pushes)


# ============================================================
# PUSH FINDER — finds all possible crate pushes from a state
# ============================================================


def find_all_pushes(reachable, crate_positions, crate_set, map_data,
                    width, height, dead_squares, targets):
    """
    Find all legal crate pushes the player can make from the current state.

    For each crate, check all 4 directions. To push a crate in a direction,
    the player must be on the opposite side (and that position must be
    reachable), and the destination must be free.

    Includes tunnel optimization: if a crate enters a 1-wide corridor
    with no side openings and no targets, push it all the way through
    to save exploring intermediate states.

    Returns a list of (push_direction_char, player_push_pos, new_crate_positions, push_count).
    """
    pushes = []

    for crate_row, crate_col in crate_positions:
        for move_char, dr, dc in DIRECTIONS:
            # To push a crate in direction (dr, dc), the player must be
            # on the opposite side: at (crate_row - dr, crate_col - dc).
            player_row = crate_row - dr
            player_col = crate_col - dc

            # The player must be able to reach that position.
            if (player_row, player_col) not in reachable:
                continue

            # The crate's destination after being pushed.
            dest_row = crate_row + dr
            dest_col = crate_col + dc

            # Check bounds.
            if dest_row < 0 or dest_row >= height:
                continue
            if dest_col < 0 or dest_col >= width:
                continue

            # Check if destination is a wall.
            if map_data[dest_row][dest_col] == '#':
                continue

            dest = (dest_row, dest_col)

            # Check if another crate is at the destination.
            if dest in crate_set:
                continue

            # Check if the destination is a dead square.
            if dest in dead_squares:
                continue

            # Always generate the normal 1-push move first.
            new_crates = []
            for crate in crate_positions:
                if crate == (crate_row, crate_col):
                    new_crates.append(dest)
                else:
                    new_crates.append(crate)
            new_crates.sort()
            new_crate_tuple = tuple(new_crates)

            # After a single push, the player ends up where the crate was.
            new_player = (crate_row, crate_col)
            pushes.append((move_char, new_player, new_crate_tuple, 1))

            # --- Tunnel Optimization ---
            # If the crate enters a tunnel (1-wide corridor with no side
            # openings), also generate a push all the way through to the
            # end as an extra option, so the search can skip intermediate states.
            tunnel_result = is_tunnel(dest_row, dest_col, dr, dc,
                                      map_data, width, height, targets)
            if tunnel_result is not None:
                tunnel_end_r, tunnel_end_c, tunnel_pushes = tunnel_result
                tunnel_end = (tunnel_end_r, tunnel_end_c)

                # Make sure the tunnel end is different from the normal dest,
                # not blocked by another crate, not a dead square, and no
                # crates are in the way along the tunnel path.
                if tunnel_end != dest and tunnel_end not in crate_set and tunnel_end not in dead_squares:
                    # Check that no other crate is along the tunnel path.
                    path_clear = True
                    check_r, check_c = dest_row + dr, dest_col + dc
                    while (check_r, check_c) != tunnel_end:
                        if (check_r, check_c) in crate_set:
                            path_clear = False
                            break
                        check_r += dr
                        check_c += dc
                    # Also check the endpoint itself for crate collision
                    # (already checked above, but double-check the path).

                    if path_clear:
                        tunnel_crates = []
                        for crate in crate_positions:
                            if crate == (crate_row, crate_col):
                                tunnel_crates.append(tunnel_end)
                            else:
                                tunnel_crates.append(crate)
                        tunnel_crates.sort()
                        tunnel_crate_tuple = tuple(tunnel_crates)

                        # Player ends up just behind the crate's final position.
                        tunnel_player = (tunnel_end[0] - dr, tunnel_end[1] - dc)
                        total_pushes = 1 + tunnel_pushes
                        pushes.append((move_char, tunnel_player, tunnel_crate_tuple, total_pushes))

    return pushes


# ============================================================
# PATH FINDING — find a walking path between two positions
# ============================================================


def find_walk_path(start, end, crate_set, map_data, width, height):
    """
    Find the shortest walking path from start to end, avoiding walls
    and crates. Uses BFS. Returns the path as a string of moves,
    or None if no path exists.
    """
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

    return None  # No path found


# ============================================================
# SOLUTION RECONSTRUCTION
# ============================================================


def reconstruct_full_path(came_from, goal_state, map_data, width, height):
    """
    Reconstruct the full move sequence from the start to the goal.

    In the push-based search, each transition is a push. But the player
    also needs to walk to the push position between pushes. This function:
    1. Traces the parent pointers from goal to start.
    2. For each push, finds the walking path to reach the push position.
    3. Combines walking + push moves into one complete solution string.
    """
    # Collect the sequence of (state, push_move, push_count) from goal back to start.
    transitions = []
    current = goal_state
    while current in came_from:
        parent_state, push_char, push_count = came_from[current]
        transitions.append((parent_state, current, push_char, push_count))
        current = parent_state

    # Reverse to get start-to-goal order.
    transitions.reverse()

    # Map each move character to its (row_change, col_change).
    direction_map = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}

    full_moves = []
    for parent_state, child_state, push_char, push_count in transitions:
        parent_player, parent_crates = parent_state
        child_player, child_crates = child_state

        # Figure out where the player needs to be to make this push.
        # The push_char tells us the direction. For a single push,
        # the player ends up where the crate was. For a tunnel push
        # with multiple pushes, the player walks alongside.
        dr, dc = direction_map[push_char]

        # Find the original crate position: the crate that changed
        # between parent and child states.
        parent_crate_set = set(parent_crates)
        child_crate_set = set(child_crates)

        old_crate = None
        for crate in parent_crates:
            if crate not in child_crate_set:
                old_crate = crate
                break

        if old_crate is None:
            # Crate didn't move (shouldn't happen).
            continue

        # The player pushes from behind the original crate position.
        push_from = (old_crate[0] - dr, old_crate[1] - dc)

        # Find the walking path from parent_player to push_from,
        # using the PARENT state's crate layout for obstacles.
        crate_set = set(parent_crates)
        walk_path = find_walk_path(parent_player, push_from, crate_set,
                                   map_data, width, height)

        if walk_path is not None:
            full_moves.append(walk_path)

        # Add the push moves (may be multiple for tunnel pushes).
        for _ in range(push_count):
            full_moves.append(push_char)

    return ''.join(full_moves)


# ============================================================
# SOKOBOT CLASS — PUSH-BASED A* SEARCH SOLVER
# ============================================================


class SokoBot:
    def solveSokobanPuzzle(self, width, height, mapData, itemsData):
        """
        Solve the Sokoban puzzle using push-based A* search.

        Instead of exploring every single player step, this solver
        only considers states where a crate is pushed. Between pushes,
        it checks whether the player can walk to the required position
        using a quick flood fill. This dramatically reduces the number
        of states to explore.

        Key optimizations:
        1. BFS-based pull distances for a wall-aware heuristic
           (much tighter than Manhattan distance).
        2. Optimal crate-to-target assignment using bitmask DP.
        3. Tunnel macros — push through 1-wide corridors in one step.
        4. Greedy tiebreaking — prefer states with lower heuristic.
        5. Static + dynamic deadlock detection.

        Parameters:
            width  (int):            Number of columns in the grid.
            height (int):            Number of rows in the grid.
            mapData  (list[list]):   Static map ('#' wall, '.' target, ' ' floor).
            itemsData (list[list]):  Movable items ('@' player, '$' crate, ' ' empty).

        Returns:
            A string of moves ('u','d','l','r') that solves the puzzle,
            or an empty string if already solved, unsolvable, or timed out.
        """
        # Record when we started so we can stop before the 15-second limit.
        start_time = time.time()
        TIME_LIMIT = 14.5  # Stop a bit early to be safe.
        TIME_CHECK_INTERVAL = 200  # Check the clock every N iterations.

        # --- Extract the initial game state ---

        player_pos = find_player_position(itemsData, width, height)
        crate_positions = find_crate_positions(itemsData, width, height)
        targets = find_target_positions(mapData, width, height)
        target_list = list(targets)

        # --- Check if the puzzle is already solved ---

        if is_goal_state(crate_positions, targets):
            return ""

        # --- Precompute dead squares ---

        dead_squares = find_dead_squares(mapData, targets, width, height)

        # --- Precompute pull distances (BFS from each target) ---
        # This gives us wall-aware distances for the heuristic.

        pull_dist = compute_pull_distances(mapData, targets, width, height)

        # --- Set up push-based A* search ---

        # State = (player_position, crate_positions_tuple)
        # The player position matters because it determines which pushes
        # are reachable next.
        initial_state = (player_pos, crate_positions)

        # Cache for heuristic values (avoids recalculating for the
        # same crate layout reached from different player positions).
        h_cache = {}
        h_start = calculate_heuristic(crate_positions, target_list, h_cache,
                                       pull_dist)

        # If the initial heuristic is infinity, no solution exists.
        if h_start == float('inf'):
            return ""

        # Priority queue: (f_score, h_tiebreak, counter, state)
        # Using h as tiebreaker means we prefer states closer to the goal
        # when f-scores are tied (greedy tiebreaking).
        counter = 0
        open_list = []
        heapq.heappush(open_list, (h_start, h_start, counter, initial_state))
        counter = counter + 1

        # g_score[state] = best known number of pushes to reach this state.
        # In push-based search, g counts pushes only (not walking steps).
        g_score = {}
        g_score[initial_state] = 0

        # came_from[state] = (parent_state, push_move_character, push_count)
        came_from = {}

        # Closed set: uses (normalized_player, crate_positions) as key.
        # This prevents reprocessing states where the player is in the
        # same connected area with the same crate layout.
        closed = set()

        # --- Run the A* search loop ---

        iterations = 0

        while len(open_list) > 0:
            # Check the time limit periodically.
            iterations = iterations + 1
            if iterations % TIME_CHECK_INTERVAL == 0:
                elapsed = time.time() - start_time
                if elapsed > TIME_LIMIT:
                    return ""

            # Pop the state with the lowest f_score.
            f_current, _h_tie, _tie, current_state = heapq.heappop(open_list)

            current_player, current_crates = current_state
            current_g = g_score.get(current_state, None)

            # Skip outdated heap entries.
            if current_g is None:
                continue
            # Re-check f-score: a better path may have been found since
            # this state was added to the queue. The cache makes this fast.
            current_h = calculate_heuristic(current_crates, target_list,
                                             h_cache, pull_dist)
            if f_current > current_g + current_h:
                continue

            # Compute the player's reachable area and normalized position.
            crate_set = set(current_crates)
            reachable, norm_player = get_reachable_area(
                current_player, crate_set, mapData, width, height
            )
            norm_key = (norm_player, current_crates)

            # Skip if this normalized state was already processed.
            if norm_key in closed:
                continue
            closed.add(norm_key)

            # Check if this state is the goal.
            if is_goal_state(current_crates, targets):
                # Reconstruct the full path including walking moves.
                return reconstruct_full_path(
                    came_from, current_state, mapData, width, height
                )

            # Find all possible pushes from ANY reachable position.
            pushes = find_all_pushes(
                reachable, current_crates, crate_set,
                mapData, width, height, dead_squares, targets
            )

            for push_char, new_player, new_crates, push_count in pushes:
                new_state = (new_player, new_crates)
                new_g = current_g + push_count

                # Only process if we found a better path to this state.
                old_g = g_score.get(new_state, float('inf'))
                if new_g < old_g:
                    # Check for dynamic deadlocks (freeze and 2x2 blocks).
                    new_crate_set = set(new_crates)
                    if is_deadlocked(new_crates, new_crate_set, targets,
                                     mapData, width, height):
                        continue  # Skip this dead-end state.

                    h = calculate_heuristic(new_crates, target_list,
                                             h_cache, pull_dist)

                    # If heuristic is infinity, this state is unreachable.
                    if h == float('inf'):
                        continue

                    g_score[new_state] = new_g
                    came_from[new_state] = (current_state, push_char, push_count)

                    f = new_g + h
                    heapq.heappush(open_list, (f, h, counter, new_state))
                    counter = counter + 1

        # The open list is empty — no solution exists.
        return ""