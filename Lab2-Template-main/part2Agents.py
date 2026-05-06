from model import (
    Location,
    Wizard,
    IceStone,
    FireStone,
    Wall,
    WizardMoves,
    GameAction,
    GameState,
    WizardSpells, NeutralStone,
)
from agents import WizardAgent

import z3
from z3 import (Solver, Bool, Bools, Int, Ints, Or, Not, And, Implies, Distinct, If)



class PuzzleWizard(WizardAgent):

    def __init__(self, initial_state):
        super().__init__(initial_state)
        self.plan = self.solve_maysu_puzzle(initial_state)

    def solve_maysu_puzzle(self, state: GameState) -> list[WizardMoves]:
        rows, cols = state.grid_size
        wizard_location = state.active_entity_location

        fire_stones = set(state.get_all_tile_locations(FireStone))
        ice_stones = set(state.get_all_tile_locations(IceStone))
        stones = fire_stones | ice_stones | {wizard_location}

        def in_bounds(r: int, c: int) -> bool:
            return 0 <= r < rows and 0 <= c < cols

        def is_valid_move(r: int, c: int) -> bool:
            return in_bounds(r, c) and not isinstance(state.tile_grid[r][c], Wall)

        directions = {
            "UP": (-1, 0),
            "DOWN": (1, 0),
            "LEFT": (0, -1),
            "RIGHT": (0, 1),
        }
        opposite_directions = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}

        open_cells = [Location(r, c) for r in range(rows) for c in range(cols) if is_valid_move(r, c)]

        edges = {}
        for loc in open_cells:
            for d, (dr, dc) in directions.items():
                nr, nc = loc.row + dr, loc.col + dc
                if is_valid_move(nr, nc):
                    edges[(loc, d)] = Bool(f"e_{loc.row}_{loc.col}_{d}")

        visited_var = {loc: Bool(f"v_{loc.row}_{loc.col}") for loc in open_cells}
        straight_var = {loc: Bool(f"s_{loc.row}_{loc.col}") for loc in open_cells}
        turn_var = {loc: Bool(f"t_{loc.row}_{loc.col}") for loc in open_cells}

        s = Solver()

        # Bidirectional edge consistency.
        for loc in open_cells:
            for d, (dr, dc) in directions.items():
                if (loc, d) not in edges:
                    continue
                nloc = Location(loc.row + dr, loc.col + dc)
                if (nloc, opposite_directions[d]) in edges:
                    s.add(edges[(loc, d)] == edges[(nloc, opposite_directions[d])])

        # Degree constraints and local shape vars.
        for loc in open_cells:
            incident = [edges[(loc, d)] for d in directions if (loc, d) in edges]
            deg = sum([If(e, 1, 0) for e in incident])

            # Cells are either unused (degree 0) or in loop (degree 2).
            s.add(If(visited_var[loc], deg == 2, deg == 0))

            up = edges[(loc, "UP")] if (loc, "UP") in edges else False
            down = edges[(loc, "DOWN")] if (loc, "DOWN") in edges else False
            left = edges[(loc, "LEFT")] if (loc, "LEFT") in edges else False
            right = edges[(loc, "RIGHT")] if (loc, "RIGHT") in edges else False

            vertical = And(up, down)
            horizontal = And(left, right)
            s.add(straight_var[loc] == Or(vertical, horizontal))
            s.add(turn_var[loc] == And(visited_var[loc], Not(straight_var[loc])))

        # Must include wizard start and all stones.
        for stone_location in stones:
            if stone_location in visited_var:
                s.add(visited_var[stone_location])

        # Fire: must turn, and both neighboring path cells (before/after) are straight.
        for fire_stone_locations in fire_stones:
            if fire_stone_locations not in visited_var:
                continue
            s.add(visited_var[fire_stone_locations])
            s.add(turn_var[fire_stone_locations])

            # If fire uses an edge toward a neighbor, that neighbor must be straight.
            for d, (dr, dc) in directions.items():
                if (fire_stone_locations, d) not in edges:
                    continue
                nloc = Location(fire_stone_locations.row + dr, fire_stone_locations.col + dc)
                if nloc in straight_var:
                    s.add(Implies(edges[(fire_stone_locations, d)], straight_var[nloc]))

        # Ice: must be straight, and at least one adjacent path cell turns.
        for ice_stone_locations in ice_stones:
            if ice_stone_locations not in visited_var:
                continue
            s.add(visited_var[ice_stone_locations])
            s.add(straight_var[ice_stone_locations])

            turn_neighbors = []
            for d, (dr, dc) in directions.items():
                if (ice_stone_locations, d) not in edges:
                    continue
                nloc = Location(ice_stone_locations.row + dr, ice_stone_locations.col + dc)
                if nloc in turn_var:
                    turn_neighbors.append(And(edges[(ice_stone_locations, d)], turn_var[nloc]))
            if turn_neighbors:
                s.add(Or(*turn_neighbors))

        # Single-loop connectivity via flow from start to every visited node.
        N = len(open_cells)
        flow_var = {}
        for loc in open_cells:
            for d, (dr, dc) in directions.items():
                if (loc, d) in edges:
                    flow_var[(loc, d)] = Int(f"f_{loc.row}_{loc.col}_{d}")
                    s.add(flow_var[(loc, d)] >= 0)
                    s.add(flow_var[(loc, d)] <= N)
                    s.add(flow_var[(loc, d)] <= If(edges[(loc, d)], N, 0))

        visited_count = sum([If(visited_var[loc], 1, 0) for loc in open_cells])
        for loc in open_cells:
            inflow = []
            outflow = []
            for d, (dr, dc) in directions.items():
                if (loc, d) in flow_var:
                    outflow.append(flow_var[(loc, d)])
                src = Location(loc.row - dr, loc.col - dc)
                if (src, d) in flow_var:
                    inflow.append(flow_var[(src, d)])

            in_sum = sum(inflow) if inflow else 0
            out_sum = sum(outflow) if outflow else 0

            if loc == wizard_location:
                s.add(out_sum - in_sum == visited_count - 1)
            else:
                s.add(in_sum - out_sum == If(visited_var[loc], 1, 0))

        if s.check() != z3.sat:
            return []

        model = s.model()

        # Build adjacency from selected edges.
        active_edges = {}
        for loc in open_cells:
            nbrs = []
            for d, (dr, dc) in directions.items():
                if (loc, d) in edges and model.evaluate(edges[(loc, d)], model_completion=True):
                    nbrs.append(Location(loc.row + dr, loc.col + dc))
            if nbrs:
                active_edges[loc] = nbrs

        if wizard_location not in active_edges:
            return []

        # Walk the unique loop and emit moves.
        moves: list[WizardMoves] = []
        old = None
        current = wizard_location
        step_limit = len(active_edges) + 5
        for _ in range(step_limit):
            nbrs = active_edges.get(current, [])
            if len(nbrs) < 2:
                return []

            next_loc = nbrs[0] if nbrs[0] != old else nbrs[1]
            rr = next_loc.row - current.row
            cc = next_loc.col - current.col
            if rr == -1 and cc == 0:
                moves.append(WizardMoves.UP)
            elif rr == 1 and cc == 0:
                moves.append(WizardMoves.DOWN)
            elif rr == 0 and cc == -1:
                moves.append(WizardMoves.LEFT)
            elif rr == 0 and cc == 1:
                moves.append(WizardMoves.RIGHT)
            else:
                return []

            old, current = current, next_loc
            if current == wizard_location:
                break

        return moves


    def react(self, state: GameState) -> WizardMoves:

        if self.plan:
            return self.plan.pop(0)

        return WizardMoves.STAY

        # TODO: YOUR CODE HERE
        # return MASYU_1_SOLUTION.pop(0)




class SpellCastingPuzzleWizard(WizardAgent):

    def react(self, state: GameState) -> GameAction:
        fire_stones = state.get_all_tile_locations(FireStone)
        ice_stones = state.get_all_tile_locations(IceStone)
        neutral_stones = state.get_all_tile_locations(NeutralStone)

        grid_size = state.grid_size
        wizard_location = state.active_entity_location

        # TODO: YOUR CODE HERE
        #return MASYU_2_SOLUTION.pop(0)






"""
Here are some reference solutions for some of the included puzzle maps you can use to help you test things
"""

MASYU_1_SOLUTION =[WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP]


MASYU_2_SOLUTION =[WizardMoves.RIGHT,WizardSpells.FIREBALL,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardSpells.FREEZE,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardSpells.FIREBALL,WizardMoves.RIGHT]
