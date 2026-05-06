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
    
    def solve_maysu_puzzle(self, state: GameState) -> list:
        rows, cols = state.grid_size
        fire_stones = set(state.get_all_tile_locations(FireStone))
        ice_stones = set(state.get_all_tile_locations(IceStone))
        stones = fire_stones | ice_stones
        wizard_location = state.active_entity_location

        def is_valid_move(r, c):
            if not (0 <= r < rows and 0 <= c < cols):
                return False
            tile = state.tile_grid[r][c]
            return not isinstance(tile, Wall)
        
        def next(loc):
            result = []
            for direction, (nrow, ncol) in [("UP", (-1, 0)), ("DOWN", (1, 0)), ("LEFT", (0, -1)), ("RIGHT", (0, 1))]:
                new_r, new_c = loc.row + nrow, loc.col + ncol
                if is_valid_move(new_r, new_c):
                    result.append((direction, Location(new_r, new_c)))
            return result
        
        edges = {}
        for r in range(rows):
            for c in range(cols):
                if is_valid_move(r, c):
                    for direction, _ in [("UP", (-1, 0)), ("DOWN", (1, 0)), ("LEFT", (0, -1)), ("RIGHT", (0, 1))]:
                        edges[(r,c, direction)] = Bool(f"edge_{r}_{c}_{direction}")

        visited_var = {}
        for r in range(rows):
            for c in range(cols):
                if is_valid_move(r, c):
                    visited_var[Location(r, c)] = Bool(f"visited_{r}_{c}")
        
        s = Solver()
        for stone_location in stones:
            s.add(visited_var[stone_location] == True)

        for r in range(rows):
            for c in range(cols):
                if not is_valid_move(r, c):
                    continue
                
                locations = Location(r, c)
                possible_edges = []
                for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    if (r, c, direction) in edges:
                        possible_edges.append(edges[(r, c, direction)])

                if_v = sum([If(edge, 1, 0) for edge in possible_edges])
                s.add(If(visited_var[locations] == True, if_v == 2, if_v == 0))

        for r in range(rows):
            for c in range(cols):
                if not is_valid_move(r, c):
                    continue

                #up
                if (r, c, "UP") in edges and (r-1, c, "DOWN") in edges:
                    s.add(edges[(r, c, "UP")] == edges[(r-1, c, "DOWN")])
                #down
                if (r, c, "DOWN") in edges and (r+1, c, "UP") in edges:
                    s.add(edges[(r, c, "DOWN")] == edges[(r+1, c, "UP")])
                #left
                if (r, c, "LEFT") in edges and (r, c-1, "RIGHT") in edges:
                    s.add(edges[(r, c, "LEFT")] == edges[(r, c-1, "RIGHT")])
                #right
                if (r, c, "RIGHT") in edges and (r, c+1, "LEFT") in edges:
                    s.add(edges[(r, c, "RIGHT")] == edges[(r, c+1, "LEFT")])
        
        for fire_stone_locations in fire_stones:
            r, c = fire_stone_locations.row, fire_stone_locations.col
            directions = ["UP", "DOWN", "LEFT", "RIGHT"]
            active_directions = [edges[(r, c, d)] for d in directions if (r, c, d) in edges]
            count = sum([If(d, 1, 0) for d in active_directions])
            s.add(count == 2)

            if (r, c, "UP") in edges and (r, c, "DOWN") in edges:
                s.add(Not(And(edges[(r, c, "UP")], edges[(r, c, "DOWN")])))
            if (r, c, "LEFT") in edges and (r, c, "RIGHT") in edges:
                s.add(Not(And(edges[(r, c, "LEFT")], edges[(r, c, "RIGHT")])))
            
        for ice_stone_locations in ice_stones:
            r, c = ice_stone_locations.row, ice_stone_locations.col
            up_down = And(edges[(r, c, "UP")], edges[(r, c, "DOWN")]) if (r, c, "UP") in edges and (r, c, "DOWN") in edges else False
            left_right = And(edges[(r, c, "LEFT")], edges[(r, c, "RIGHT")]) if (r, c, "LEFT") in edges and (r, c, "RIGHT") in edges else False

            if isinstance(up_down, bool):
                s.add(left_right)
            elif isinstance(left_right, bool):
                s.add(up_down)
            else:
                s.add(Or(up_down, left_right))

        #SOLVING THIS SHIT BRUH

        while s.check() == z3.sat:
            model = s.model()
            
            active_edges = {}
            for (r, c, direction), edge_variable in edges.items():
                if model.evaluate(edge_variable):
                    loc = Location(r, c)
                    if loc not in active_edges:
                        active_edges[loc] = []
                    active_edges[loc].append(direction)

            repeating_cells = set()
            for loc in active_edges.keys():
                repeating_cells.add(loc)
        
            if self.is_single_connected(repeating_cells, active_edges):
                moves = self.extracting_moves(wizard_location, active_edges)
                return moves

            block = And([edges[(r, c, d)] == model.evaluate(edges[(r, c, d)]) for (r, c, d) in edges.keys()])
            s.add(Not(block))
        
        return [] #for no val solution
    
    def is_single_connected(self, repeating_cells, active_edges):
        
        if not repeating_cells:
            return False
        
        start = next(iter(repeating_cells))
        visited = set()
        queue = [start]
        visited.add(start)

        while queue:
            current = queue.pop(0)
            r, c = current.row, current.col
            for direction in active_edges.get(current, []):
                if direction == "UP":
                    new_loc = Location(r-1, c)
                elif direction == "DOWN":
                    new_loc = Location(r+1, c)
                elif direction == "LEFT":
                    new_loc = Location(r, c-1)
                else: #RIGHT
                    new_loc = Location(r, c+1)

                if new_loc in repeating_cells and new_loc not in visited:
                    visited.add(new_loc)
                    queue.append(new_loc)
        
        return len(visited) == len(repeating_cells)
    
    def extracting_moves(self, start, active_edges):
        moves = []
        current = start
        old = None

        for _ in range(1000):
            if current not in active_edges:
                break
        
            next_loc = None
            for direction in active_edges[current]:
                r, c = current.row, current.col
                if direction == "UP":
                    candidate = Location(r-1, c)
                elif direction == "DOWN":
                    candidate = Location(r+1, c)
                elif direction == "LEFT":
                    candidate = Location(r, c-1)
                else: #RIGHT
                    candidate = Location(r, c+1)
                
                if candidate != old:
                    next_loc = candidate
                    break
            
            if next_loc is None:
                break
            
            rr = next_loc.row - current.row
            cc = next_loc.col - current.col

            if rr == -1:
                moves.append(WizardMoves.UP)
            elif rr == 1:
                moves.append(WizardMoves.DOWN)
            elif cc == -1:
                moves.append(WizardMoves.LEFT)
            else:
                moves.append(WizardMoves.RIGHT)
            
            if next_loc == start:
                break

            old = current
            current = next_loc
        
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
        return MASYU_2_SOLUTION.pop(0)






"""
Here are some reference solutions for some of the included puzzle maps you can use to help you test things
"""

MASYU_1_SOLUTION =[WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP]


MASYU_2_SOLUTION =[WizardMoves.RIGHT,WizardSpells.FIREBALL,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.DOWN,WizardSpells.FREEZE,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.LEFT,WizardMoves.DOWN,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardMoves.RIGHT,WizardMoves.UP,WizardMoves.UP,WizardMoves.UP,WizardMoves.LEFT,WizardMoves.UP,WizardMoves.UP,WizardSpells.FIREBALL,WizardMoves.RIGHT]
