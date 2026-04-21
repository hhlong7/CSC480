from model import (
    Location,
    Portal,
    Wizard,
    Goblin,
    Crystal,
    WizardMoves,
    GoblinMoves,
    GameAction,
    GameState,
)
from agents import ReasoningWizard
from dataclasses import dataclass


class WizardGreedy(ReasoningWizard):
    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return float("-inf")
        wizard_loc = wizard_loc[0]
        portal_loc = state.get_all_tile_locations(Portal)[0]
        remaining_crystals = state.get_all_entity_locations(Crystal)
        goblin_loc = state.get_all_entity_locations(Goblin)

        distance_to_portal = abs(wizard_loc.row - portal_loc.row) + abs(wizard_loc.col - portal_loc.col)
        goblin_distance = (min(abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col) 
                              for g in goblin_loc )
            if goblin_loc else 1.0
        )
        portal_term = 1.0 / (distance_to_portal + 1.0)
        safety_term = goblin_distance / (goblin_distance + 1.0)
        crystal_term = 1.0 / (len(remaining_crystals) + 1.0)
        score = state.score / (state.score + 1.0)

        return (
            0.9 * score + 0.8 * portal_term + 0.7 * safety_term + 0.6 * crystal_term
        )
        #raise NotImplementedError


class WizardMiniMax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return -1.0
        wizard_loc = wizard_loc[0]
        portal_loc = state.get_all_tile_locations(Portal)[0]
        remaining_crystals = state.get_all_entity_locations(Crystal)
        goblin_loc = state.get_all_entity_locations(Goblin)

        distance_to_portal = abs(wizard_loc.row - portal_loc.row) + abs(wizard_loc.col - portal_loc.col)
        goblin_distance = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_loc
            )
            if goblin_loc
            else 1.0
        )
        portal_term = 1.0 / (distance_to_portal + 1.0)
        safety_term = goblin_distance / (goblin_distance + 1.0)
        crystal_term = 1.0 / (len(remaining_crystals) + 1.0)
        score = state.score / (state.score + 1.0)
        return (
            0.9 * score + 0.8 * portal_term + 0.7 * safety_term + 0.6 * crystal_term
        )
        #raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)
        #raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        best_move = WizardMoves.STAY
        best_value = float("-inf")

        for action, successor in self.get_successors(state):
            if not isinstance(action, WizardMoves):
                continue
            value = self.minimax(successor, 1)
            if value > best_value:
                best_value = value
                best_move = action
        return best_move
        #raise NotImplementedError


    def minimax(self, state: GameState, depth: int):
        # TODO YOUR CODE HERE
        if self.is_terminal(state):
            return self.evaluation(state)
        active_entity = state.get_active_entity()

        if isinstance(active_entity, Wizard):
            if depth > self.max_depth:
                return self.evaluation(state)
            successors = self.get_successors(state)
            if not successors:
                return self.evaluation(state)
            
            value = float("-inf")
            for _, successor in successors:
                value = max(value, self.minimax(successor, depth + 1))
            return value
        
        successors = self.get_successors(state)
        if not successors:
            return self.evaluation(state)
        value = float("inf")
        for _, successor in successors:
            value = min(value, self.minimax(successor, depth))
        return value
        
        #raise NotImplementedError


class WizardAlphaBeta(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return -1.0
        wizard_loc = wizard_loc[0]
        portal_loc = state.get_all_tile_locations(Portal)[0]
        remaining_crystals = state.get_all_entity_locations(Crystal)
        goblin_loc = state.get_all_entity_locations(Goblin)

        distance_to_portal = abs(wizard_loc.row - portal_loc.row) + abs(wizard_loc.col - portal_loc.col)
        goblin_distance = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_loc
            )
            if goblin_loc
            else 1.0
        )
        portal_term = 1.0 / (distance_to_portal + 1.0)
        safety_term = goblin_distance / (goblin_distance + 1.0)
        crystal_term = 1.0 / (len(remaining_crystals) + 1.0)
        score = state.score / (state.score + 1.0)
        return (
            0.9 * score + 0.8 * portal_term + 0.7 * safety_term + 0.6 * crystal_term
        )
        #raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)
        #raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        best_move = WizardMoves.STAY
        best_value = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        successors = list(self.get_successors(state))
        successors.sort(key=lambda x: self.evaluation(x[1]), reverse=True)

        for action, successor in successors:
            if not isinstance(action, WizardMoves):
                continue
            value = self.alpha_beta_minimax(successor, 1, alpha, beta)
            if value > best_value:
                best_value = value
                best_move = action
            alpha = max(alpha, best_value)
        return best_move
        #raise NotImplementedError


    def alpha_beta_minimax(self, state: GameState, depth: int, alpha: float, beta: float):
        # TODO YOUR CODE HERE
        if self.is_terminal(state):
            return self.evaluation(state)
        active_entity = state.get_active_entity()
        successors = list(self.get_successors(state))
        if not successors:
            return self.evaluation(state)
        if isinstance(active_entity, Wizard):
            if depth > self.max_depth:
                return self.evaluation(state)
            successors.sort(key=lambda x: self.evaluation(x[1]), reverse=True)
    
            value = float("-inf")
            for _, successor in successors:
                value = max(value, self.alpha_beta_minimax(successor, depth + 1, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        
        successors.sort(key=lambda x: self.evaluation(x[1]))
        value = float("inf")
        for _, successor in successors:
            value = min(value, self.alpha_beta_minimax(successor, depth, alpha, beta))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value
        #raise NotImplementedError




class WizardExpectimax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return -1.0
        wizard_loc = wizard_loc[0]
        portal_loc = state.get_all_tile_locations(Portal)[0]
        remaining_crystals = state.get_all_entity_locations(Crystal)
        goblin_loc = state.get_all_entity_locations(Goblin)

        distance_to_portal = abs(wizard_loc.row - portal_loc.row) + abs(wizard_loc.col - portal_loc.col)
        goblin_distance = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_loc
            )
            if goblin_loc
            else 1.0
        )
        portal_term = 1.0 / (distance_to_portal + 1.0)
        safety_term = goblin_distance / (goblin_distance + 1.0)
        crystal_term = 1.0 / (len(remaining_crystals) + 1.0)
        score = state.score / (state.score + 1.0)
        return (
            0.9 * score + 0.8 * portal_term + 0.7 * safety_term + 0.6 * crystal_term
        )
        #raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)
        #raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        best_move = WizardMoves.STAY
        best_value = float("-inf")

        for action, successor in self.get_successors(state):
            if not isinstance(action, WizardMoves):
                continue
            value = self.expectimax(successor, 1)
            if value > best_value:
                best_value = value
                best_move = action
        return best_move
        #raise NotImplementedError


    def expectimax(self, state: GameState, depth: int):
        # TODO YOUR CODE HERE
        if self.is_terminal(state):
            return self.evaluation(state)
        active_entity = state.get_active_entity()
        successors = self.get_successors(state)
        if not successors:
            return self.evaluation(state)
        
        if isinstance(active_entity, Wizard):
            if depth > self.max_depth:
                return self.evaluation(state)
            value = float("-inf")
            for _, successor in successors:
                value = max(value, self.expectimax(successor, depth + 1))
            return value
        total_value = 0.0
        for _, successor in successors:
            total_value += self.expectimax(successor, depth)
        return total_value / len(successors)
        #raise NotImplementedError
