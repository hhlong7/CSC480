from model import (
    Location,
    Portal,
    EmptyEntity,
    Wizard,
    Goblin,
    Crystal,
    WizardMoves,
    GoblinMoves,
    GameAction,
    GameState,
)
from agents import WizardSearchAgent
import heapq
from dataclasses import dataclass


class WizardDFS(WizardSearchAgent):
    @dataclass(eq=True, frozen=True, order=True)
    class SearchState:
        wizard_loc: Location
        portal_loc: Location

    paths: dict[SearchState, list[WizardMoves]] = {}
    search_stack: list[SearchState] = []
    initial_game_state: GameState

    def search_to_game(self, search_state: SearchState) -> GameState:
        initial_wizard_loc = self.initial_game_state.active_entity_location
        initial_wizard = self.initial_game_state.get_active_entity()

        new_game_state = (
            self.initial_game_state.replace_entity(
                initial_wizard_loc.row, initial_wizard_loc.col, EmptyEntity()
            )
            .replace_entity(
                search_state.wizard_loc.row, search_state.wizard_loc.col, initial_wizard
            )
            .replace_active_entity_location(search_state.wizard_loc)
        )

        return new_game_state

    def game_to_search(self, game_state: GameState) -> SearchState:
        wizard_loc = game_state.active_entity_location
        portal_loc = game_state.get_all_tile_locations(Portal)[0]
        return self.SearchState(wizard_loc, portal_loc)

    def __init__(self, initial_state: GameState):
        self.start_search(initial_state)

    def start_search(self, game_state: GameState):
        self.initial_game_state = game_state

        initial_search_state = self.game_to_search(game_state)
        self.paths = {}
        self.paths[initial_search_state] = []
        self.search_stack = [initial_search_state]

    def is_goal(self, state: SearchState) -> bool:
        return state.wizard_loc == state.portal_loc

    def next_search_expansion(self) -> GameState | None:
        # TODO: YOUR CODE HERE
        while self.search_stack:
            ns = self.search_stack.pop()
            if self.is_goal(ns):
                self.plan = list(reversed(self.paths[ns]))
                return None
            return self.search_to_game(ns)
        return None
        #raise NotImplementedError

    def process_search_expansion(
        self, source: GameState, target: GameState, action: WizardMoves
    ) -> None:
        # TODO: YOUR CODE HERE
        source_search_state = self.game_to_search(source)
        target_search_state = self.game_to_search(target)
        if target_search_state not in self.paths:
            self.paths[target_search_state] = self.paths[source_search_state] + [action]
            self.search_stack.append(target_search_state)
        #raise NotImplementedError


class WizardBFS(WizardSearchAgent):
    @dataclass(eq=True, frozen=True, order=True)
    class SearchState:
        wizard_loc: Location
        portal_loc: Location

    paths: dict[SearchState, list[WizardMoves]] = {}
    search_stack: list[SearchState] = []
    initial_game_state: GameState

    def search_to_game(self, search_state: SearchState) -> GameState:
        initial_wizard_loc = self.initial_game_state.active_entity_location
        initial_wizard = self.initial_game_state.get_active_entity()

        new_game_state = (
            self.initial_game_state.replace_entity(
                initial_wizard_loc.row, initial_wizard_loc.col, EmptyEntity()
            )
            .replace_entity(
                search_state.wizard_loc.row, search_state.wizard_loc.col, initial_wizard
            )
            .replace_active_entity_location(search_state.wizard_loc)
        )

        return new_game_state

    def game_to_search(self, game_state: GameState) -> SearchState:
        wizard_loc = game_state.active_entity_location
        portal_loc = game_state.get_all_tile_locations(Portal)[0]
        return self.SearchState(wizard_loc, portal_loc)

    def __init__(self, initial_state: GameState):
        self.start_search(initial_state)

    def start_search(self, game_state: GameState):
        self.initial_game_state = game_state

        initial_search_state = self.game_to_search(game_state)
        self.paths = {}
        self.paths[initial_search_state] = []
        self.search_stack = [initial_search_state]

    def is_goal(self, state: SearchState) -> bool:
        return state.wizard_loc == state.portal_loc

    def next_search_expansion(self) -> GameState | None:
        # TODO: YOUR CODE HERE
        while self.search_stack:
            ns = self.search_stack.pop(0)
            if self.is_goal(ns):
                self.plan = list(reversed(self.paths[ns]))
                return None
            return self.search_to_game(ns)
        return None
        #raise NotImplementedError

    def process_search_expansion(
        self, source: GameState, target: GameState, action: WizardMoves
    ) -> None:
        # TODO: YOUR CODE HERE
        source_search_state = self.game_to_search(source)
        target_search_state = self.game_to_search(target)
        if target_search_state not in self.paths:
            self.paths[target_search_state] = self.paths[source_search_state] + [action]
            self.search_stack.append(target_search_state)
        #raise NotImplementedError


class WizardAstar(WizardSearchAgent):
    @dataclass(eq=True, frozen=True, order=True)
    class SearchState:
        wizard_loc: Location
        portal_loc: Location

    paths: dict[SearchState, tuple[float, list[WizardMoves]]] = {}
    search_pq: list[tuple[float, SearchState]] = []
    initial_game_state: GameState

    def search_to_game(self, search_state: SearchState) -> GameState:
        initial_wizard_loc = self.initial_game_state.active_entity_location
        initial_wizard = self.initial_game_state.get_active_entity()

        new_game_state = (
            self.initial_game_state.replace_entity(
                initial_wizard_loc.row, initial_wizard_loc.col, EmptyEntity()
            )
            .replace_entity(
                search_state.wizard_loc.row, search_state.wizard_loc.col, initial_wizard
            )
            .replace_active_entity_location(search_state.wizard_loc)
        )

        return new_game_state

    def game_to_search(self, game_state: GameState) -> SearchState:
        wizard_loc = game_state.active_entity_location
        portal_loc = game_state.get_all_tile_locations(Portal)[0]
        return self.SearchState(wizard_loc, portal_loc)

    def __init__(self, initial_state: GameState):
        self.start_search(initial_state)

    def start_search(self, game_state: GameState):
        self.initial_game_state = game_state

        initial_search_state = self.game_to_search(game_state)
        self.paths = {}
        self.paths[initial_search_state] = 0, []
        self.search_pq = [(0, initial_search_state)]

    def is_goal(self, state: SearchState) -> bool:
        return state.wizard_loc == state.portal_loc

    def cost(self, source: GameState, target: GameState, action: WizardMoves) -> float:
        return 1

    def heuristic(self, target: GameState) -> float: #manhattan dist
        # TODO: YOUR CODE HERE
        wizard_loc = target.active_entity_location
        portal_loc = target.get_all_tile_locations(Portal)[0]
        dist = abs(wizard_loc.row - portal_loc.row) + abs(wizard_loc.col - portal_loc.col)
        return dist
        #raise NotImplementedError

    def next_search_expansion(self) -> GameState | None:
        # TODO: YOUR CODE HERE
        while self.search_pq:
            estimated_cost, ns = heapq.heappop(self.search_pq)
            true_cost, _ = self.paths[ns]
            if estimated_cost > true_cost + self.heuristic(self.search_to_game(ns)):
                continue
            if self.is_goal(ns):
                self.plan = list(reversed(self.paths[ns][1]))
                return None
            return self.search_to_game(ns)
        return None
        #raise NotImplementedError

    def process_search_expansion(
        self, source: GameState, target: GameState, action: WizardMoves
    ) -> None:
        # TODO: YOUR CODE HERE
        source_search_state = self.game_to_search(source)
        target_search_state = self.game_to_search(target)
        new_cost = self.paths[source_search_state][0] + self.cost(source, target, action)
        if target_search_state not in self.paths or new_cost < self.paths[target_search_state][0]:
            self.paths[target_search_state] = (new_cost, self.paths[source_search_state][1] + [action])
            estimated_cost = new_cost + self.heuristic(target)
            heapq.heappush(self.search_pq, (estimated_cost, target_search_state))
        
        #raise NotImplementedError


class CrystalSearchWizard(WizardSearchAgent):
    # TODO: YOUR CODE HERE
    # Use A* but have to take in account for the crystal

    def __init__(self, initial_state: GameState):
        self.start_search(initial_state)

    def cost(self, source: GameState, target: GameState, action: WizardMoves) -> float:
        return 1

    def next_search_expansion(self) -> GameState | None:
        # TODO YOUR CODE HERE
        while self.search_pq:
            estimated_cost, ns = heapq.heappop(self.search_pq)
            true_cost, _ = self.paths[ns]
            if estimated_cost > true_cost + self.heuristic(ns):
                continue
            if self.is_goal(ns):
                self.plan = list(reversed(self.paths[ns][1]))
                return None
            return self.search_to_game(ns)
        return None
        #raise NotImplementedError

    def process_search_expansion(
        self, source: GameState, target: GameState, action: WizardMoves
    ) -> None:
        # TODO YOUR CODE HERE
        source_search_state = self.game_to_search(source)
        target_search_state = self.game_to_search(target)
        new_cost = self.paths[source_search_state][0] + self.cost(source, target, action)
        if target_search_state not in self.paths or new_cost < self.paths[target_search_state][0]:
            self.paths[target_search_state] = (new_cost, self.paths[source_search_state][1] + [action])
            estimated_cost = new_cost + self.heuristic(target_search_state)
            heapq.heappush(self.search_pq, (estimated_cost, target_search_state))
        #raise NotImplementedError



class SuboptimalCrystalSearchWizard(CrystalSearchWizard):
    #crystal search but its unoptimal lol, => overestimate?
    def heuristic(self, target: SearchState) -> float:
        # TODO YOUR CODE HERE
        if not target.remaining_crystals:
            return abs(target.wizard_loc.row - target.portal_loc.row) + abs(target.wizard_loc.col - target.portal_loc.col)
        total = 0
        current_loc = target.wizard_loc
        remaining_crystals = set(target.remaining_crystals)
        while remaining_crystals:
            closest_crystal = min(remaining_crystals, key=lambda c: abs(current_loc.row - c.row) + abs(current_loc.col - c.col))
            total += abs(current_loc.row - closest_crystal.row) + abs(current_loc.col - closest_crystal.col)
            current_loc = closest_crystal
            remaining_crystals.remove(closest_crystal)
        total += abs(current_loc.row - target.portal_loc.row) + abs(current_loc.col - target.portal_loc.col)
        return total
        #raise NotImplementedError
