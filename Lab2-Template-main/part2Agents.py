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

        open_moves = [Location(r, c) for r in range(rows) for c in range(cols) if is_valid_move(r, c)]

        edges = {}
        for loc in open_moves:
            for d, (dr, dc) in directions.items():
                nr, nc = loc.row + dr, loc.col + dc
                if is_valid_move(nr, nc):
                    edges[(loc, d)] = Bool(f"e_{loc.row}_{loc.col}_{d}")

        visited_var = {loc: Bool(f"v_{loc.row}_{loc.col}") for loc in open_moves}
        straight_var = {loc: Bool(f"s_{loc.row}_{loc.col}") for loc in open_moves}
        turn_var = {loc: Bool(f"t_{loc.row}_{loc.col}") for loc in open_moves}

        s = Solver()

        for loc in open_moves:
            for d, (dr, dc) in directions.items():
                if (loc, d) not in edges:
                    continue
                nloc = Location(loc.row + dr, loc.col + dc)
                if (nloc, opposite_directions[d]) in edges:
                    s.add(edges[(loc, d)] == edges[(nloc, opposite_directions[d])])

        for loc in open_moves:
            cell = [edges[(loc, d)] for d in directions if (loc, d) in edges]
            degree = sum([If(e, 1, 0) for e in cell])

            s.add(If(visited_var[loc], degree == 2, degree == 0))

            up = edges[(loc, "UP")] if (loc, "UP") in edges else False
            down = edges[(loc, "DOWN")] if (loc, "DOWN") in edges else False
            left = edges[(loc, "LEFT")] if (loc, "LEFT") in edges else False
            right = edges[(loc, "RIGHT")] if (loc, "RIGHT") in edges else False

            vertical = And(up, down)
            horizontal = And(left, right)
            s.add(straight_var[loc] == Or(vertical, horizontal))
            s.add(turn_var[loc] == And(visited_var[loc], Not(straight_var[loc])))

        for stone_location in stones:
            if stone_location in visited_var:
                s.add(visited_var[stone_location])

        for fire_stone_locations in fire_stones:
            if fire_stone_locations not in visited_var:
                continue
            s.add(visited_var[fire_stone_locations])
            s.add(turn_var[fire_stone_locations])

            for d, (dr, dc) in directions.items():
                if (fire_stone_locations, d) not in edges:
                    continue
                nloc = Location(fire_stone_locations.row + dr, fire_stone_locations.col + dc)
                if nloc in straight_var:
                    s.add(Implies(edges[(fire_stone_locations, d)], straight_var[nloc]))

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

        n = len(open_moves)
        v = {}
        for loc in open_moves:
            for d, (dr, dc) in directions.items():
                if (loc, d) in edges:
                    v[(loc, d)] = Int(f"f_{loc.row}_{loc.col}_{d}")
                    s.add(v[(loc, d)] >= 0)
                    s.add(v[(loc, d)] <= n)
                    s.add(v[(loc, d)] <= If(edges[(loc, d)], n, 0))

        visited_count = sum([If(visited_var[loc], 1, 0) for loc in open_moves])
        for loc in open_moves:
            inn = []
            outt = []
            for d, (dr, dc) in directions.items():
                if (loc, d) in v:
                    outt.append(v[(loc, d)])
                src = Location(loc.row - dr, loc.col - dc)
                if (src, d) in v:
                    inn.append(v[(src, d)])

            in_sum = sum(inn) if inn else 0
            out_sum = sum(outt) if outt else 0

            if loc == wizard_location:
                s.add(out_sum - in_sum == visited_count - 1)
            else:
                s.add(in_sum - out_sum == If(visited_var[loc], 1, 0))

        if s.check() != z3.sat:
            return []

        model = s.model()

        active_edges = {}
        for loc in open_moves:
            nbrs = []
            for d, (dr, dc) in directions.items():
                if (loc, d) in edges and model.evaluate(edges[(loc, d)], model_completion=True):
                    nbrs.append(Location(loc.row + dr, loc.col + dc))
            if nbrs:
                active_edges[loc] = nbrs

        if wizard_location not in active_edges:
            return []

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
        # return MASYU_1_SOLUTION.pop(0)

class SpellCastingPuzzleWizard(WizardAgent):

    def __init__(self, initial_state):
        super().__init__(initial_state)
        self.plan = self.solve_maysu_puzzle(initial_state)
    
    def solve_maysu_puzzle(self, state: GameState) -> list[GameAction]:
        rows, cols = state.grid_size
        wizard_location = state.active_entity_location

        fire_stones = set(state.get_all_tile_locations(FireStone))
        ice_stones = set(state.get_all_tile_locations(IceStone))
        neutral_stones = set(state.get_all_tile_locations(NeutralStone))

        stones = fire_stones | ice_stones | neutral_stones | {wizard_location}
        def in_bounds(r: int, c: int) -> bool:
            return 0 <= r < rows and 0 <= c < cols
        
        def is_valid_move(r: int, c: int) -> bool:
            return in_bounds(r, c) and not isinstance(state.tile_grid[r][c], Wall)
        
        directions = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}

        opposite_dir = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}

        open_moves = [Location(r, c) for r in range(rows) for c in range(cols) if is_valid_move(r, c)]
        edges = {}
        for location in open_moves:
            for d, (rr, cc) in directions.items():
                nrow, ncol = location.row + rr, location.col + cc
                if is_valid_move(nrow, ncol):
                    edges[(location, d)] = Bool(f"edge_{location.row}_{location.col}_{d}")
        
        visited_var = {loc: Bool(f"visited_{loc.row}_{loc.col}") for loc in open_moves}

        straight_var = {loc: Bool(f"straight_{loc.row}_{loc.col}") for loc in open_moves}

        turn_var = {loc: Bool(f"turn_{loc.row}_{loc.col}") for loc in open_moves}

        stone_type = {}
        for stone_loc in fire_stones | ice_stones | neutral_stones:
            stone_type[stone_loc] = Int(f"stone_type_{stone_loc.row}_{stone_loc.col}")
        
        optimizer = z3.Solver()
        for stone_loc in stone_type:
            optimizer.add(Or(stone_type[stone_loc] == 0, stone_type[stone_loc] == 1))

        for loc in open_moves:
            for d, (rr, cc) in directions.items():
                if (loc, d) not in edges:
                    continue
                nloc = Location(loc.row + rr, loc.col + cc)
                opposite = opposite_dir[d]

                if (nloc, opposite) in edges:
                    optimizer.add(edges[(loc, d)] == edges[(nloc, opposite)])
        
        for loc in open_moves:
            possible = [edges[(loc, d)] for d in directions if (loc, d) in edges]

            if_v = sum([If(edge_var, 1, 0) for edge_var in possible])
            optimizer.add(If(visited_var[loc], if_v == 2, if_v == 0))

            up = edges[(loc, "UP")] if (loc, "UP") in edges else False
            down = edges[(loc, "DOWN")] if (loc, "DOWN") in edges else False
            left = edges[(loc, "LEFT")] if (loc, "LEFT") in edges else False
            right = edges[(loc, "RIGHT")] if (loc, "RIGHT") in edges else False

            vertical = And(up, down)
            horizontal = And(left, right)

            optimizer.add(straight_var[loc] == Or(vertical, horizontal))
            optimizer.add(turn_var[loc] == And(visited_var[loc], Not(straight_var[loc])))

        for stone_loc in stones:
            if stone_loc in visited_var:
                optimizer.add(visited_var[stone_loc])
        
        for stone_loc in fire_stones | ice_stones | neutral_stones:
            optimizer.add(visited_var[stone_loc])
            fire = stone_type[stone_loc] == 0
            ice = stone_type[stone_loc] == 1
            optimizer.add(Implies(fire, turn_var[stone_loc]))

            for d, (rr, cc) in directions.items():
                if (stone_loc, d) not in edges:
                    continue
                nloc = Location(stone_loc.row + rr, stone_loc.col + cc)
                if nloc in straight_var:
                    optimizer.add(Implies(And(fire, edges[(stone_loc, d)]), straight_var[nloc]))
                
            optimizer.add(Implies(ice, straight_var[stone_loc]))
            turn_neighbors = []
            for d, (rr, cc) in directions.items():
                if (stone_loc, d) not in edges:
                    continue
                nloc = Location(stone_loc.row + rr, stone_loc.col + cc)
                if nloc in turn_var:
                    turn_neighbors.append(And(edges[(stone_loc, d)], turn_var[nloc]))
            
            if turn_neighbors:
                optimizer.add(Implies(ice, Or(*turn_neighbors)))
        
        n = len(open_moves)
        v = {}

        for loc in open_moves:
            for d, (rr, cc) in directions.items():
                if (loc, d) in edges:
                    v[(loc, d)] = Int(f"flow_{loc.row}_{loc.col}_{d}")
                    optimizer.add(v[(loc, d)] >= 0)
                    optimizer.add(v[(loc, d)] <= n)
                    optimizer.add(v[(loc, d)] <= If(edges[(loc, d)], n, 0))
        
        visited_count = sum([If(visited_var[loc], 1, 0) for loc in open_moves])

        for loc in open_moves:
            inflow = []
            outflow = []
            for d, (rr, cc) in directions.items():
                if (loc, d) in v:
                    outflow.append(v[(loc, d)])
                src = Location(loc.row - rr, loc.col - cc)
                if (src, d) in v:
                    inflow.append(v[(src, d)])
            
            in_sum = sum(inflow) if inflow else 0
            out_sum = sum(outflow) if outflow else 0

            if loc == wizard_location:
                optimizer.add(out_sum - in_sum == visited_count - 1)
            else:
                optimizer.add(in_sum - out_sum == If(visited_var[loc], 1, 0))

        #stone_type 0 = fire, 1 = ice
        #changing a fire stone to ice costs FREEZE=10; changing ice to fire costs FIREBALL=15
        #neutral stone always needs a spell: FIREBALL=15 if type==0, FREEZE=10 if type==1
        
        mana = []
        for stone_loc in fire_stones:
            mana.append(If(stone_type[stone_loc] == 1, 10, 0))
        for stone_loc in ice_stones:
            mana.append(If(stone_type[stone_loc] == 0, 15, 0))
        for stone_loc in neutral_stones:
            mana.append(If(stone_type[stone_loc] == 0, 15, 10))
        total_mana_expr = sum(mana) if mana else 0

        max_possible_mana = len(fire_stones) * 10 + len(ice_stones) * 15 + len(neutral_stones) * 15
        model = None
        for budget in range(0, max_possible_mana + 1, 5):
            optimizer.push()
            optimizer.add(total_mana_expr <= budget)
            result = optimizer.check()
            if result == z3.sat:
                model = optimizer.model()
                optimizer.pop()
                break
            optimizer.pop()

        if model is None:
            return []
        
        active_edges = {}
        for loc in open_moves:
            nbrs = []
            for d, (rr, cc) in directions.items():
                if (loc, d) in edges and model.evaluate(edges[(loc, d)], model_completion=True):
                    nbrs.append(Location(loc.row + rr, loc.col + cc))
            if nbrs:
                active_edges[loc] = nbrs
        
        if wizard_location not in active_edges:
            return []
        
        spell_actions = {}

        for stone_loc in fire_stones | ice_stones | neutral_stones:
            final = model.evaluate(stone_type[stone_loc], model_completion=True).as_long()

            if stone_loc in neutral_stones:
                if final == 0:
                    spell_actions[stone_loc] = WizardSpells.FIREBALL
                else:
                    spell_actions[stone_loc] = WizardSpells.FREEZE
            elif stone_loc in fire_stones:
                if final == 1:
                    spell_actions[stone_loc] = WizardSpells.FREEZE
            elif stone_loc in ice_stones:
                if final == 0:
                    spell_actions[stone_loc] = WizardSpells.FIREBALL
    
        moves = []
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
        
        actions = []
        casted_stones = set()
        current = wizard_location

        if current in spell_actions:
            actions.append(spell_actions[current])
            casted_stones.add(current)
        
        for move in moves:
            actions.append(move)
            dr, dc = move.value
            current = Location(current.row + dr, current.col + dc)

            if current == wizard_location:
                continue

            if current in spell_actions and current not in casted_stones:
                actions.append(spell_actions[current])
                casted_stones.add(current)
        
        return actions


    def react(self, state: GameState) -> GameAction:
        if self.plan:
            return self.plan.pop(0)
        return WizardMoves.STAY
        #return MASYU_2_SOLUTION.pop(0)


"""
Here are some reference solutions for some of the included puzzle maps you can use to help you test things
"""

MASYU_1_SOLUTION =[WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP]


MASYU_2_SOLUTION =[WizardMoves.RIGHT,WizardSpells.FIREBALL,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardSpells.FREEZE,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardSpells.FIREBALL,WizardMoves.RIGHT]
