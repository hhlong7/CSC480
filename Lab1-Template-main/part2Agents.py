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
class WizardGreedy(ReasoningWizard):
    def evaluation(self, state: GameState) -> float:
        wizard_locs = state.get_all_entity_locations(Wizard)
        if not wizard_locs:
            return -1000000.0

        wizard_loc = wizard_locs[0]
        if isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal):
            return 1000000.0 + 1000.0 * state.score

        portal_loc = state.get_all_tile_locations(Portal)[0]
        goblin_locs = state.get_all_entity_locations(Goblin)

        portal_dist = abs(wizard_loc.row - portal_loc.row) + abs(
            wizard_loc.col - portal_loc.col
        )
        nearest_goblin_dist = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_locs
            )
            if goblin_locs
            else 10.0
        )

        danger_penalty = (
            -500.0 if nearest_goblin_dist <= 1 else (-120.0 if nearest_goblin_dist == 2 else 0.0)
        )
        return 200.0 * state.score - 80.0 * portal_dist + danger_penalty


class WizardMiniMax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        wizard_locs = state.get_all_entity_locations(Wizard)
        if not wizard_locs:
            return -1000000.0

        wizard_loc = wizard_locs[0]
        if isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal):
            return 1000000.0 + 1000.0 * state.score

        portal_loc = state.get_all_tile_locations(Portal)[0]
        goblin_locs = state.get_all_entity_locations(Goblin)

        portal_dist = abs(wizard_loc.row - portal_loc.row) + abs(
            wizard_loc.col - portal_loc.col
        )
        nearest_goblin_dist = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_locs
            )
            if goblin_locs
            else 10.0
        )

        danger_penalty = (
            -500.0 if nearest_goblin_dist <= 1 else (-120.0 if nearest_goblin_dist == 2 else 0.0)
        )
        return 200.0 * state.score - 80.0 * portal_dist + danger_penalty

    def is_terminal(self, state: GameState) -> bool:
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)

    def react(self, state: GameState) -> WizardMoves:
        wizard_loc = state.get_all_entity_locations(Wizard)[0]
        goblin_locs = state.get_all_entity_locations(Goblin)
        nearest_goblin_dist = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_locs
            )
            if goblin_locs
            else 10.0
        )

        if state.turn >= 60 or (state.turn >= 38 and nearest_goblin_dist > 2):
            portal_loc = state.get_all_tile_locations(Portal)[0]
            best_move = WizardMoves.STAY
            best_dist = float("inf")
            for action, successor in self.get_successors(state):
                if not isinstance(action, WizardMoves):
                    continue
                wizard_locs = successor.get_all_entity_locations(Wizard)
                if not wizard_locs:
                    continue
                wizard_loc = wizard_locs[0]
                dist = abs(wizard_loc.row - portal_loc.row) + abs(
                    wizard_loc.col - portal_loc.col
                )
                if dist < best_dist or (
                    dist == best_dist
                    and best_move == WizardMoves.STAY
                    and action != WizardMoves.STAY
                ):
                    best_dist = dist
                    best_move = action
            return best_move

        best_move = WizardMoves.STAY
        best_value = float("-inf")

        for action, successor in self.get_successors(state):
            if not isinstance(action, WizardMoves):
                continue
            value = self.minimax(successor, 1)
            if value > best_value or (
                value == best_value
                and best_move == WizardMoves.STAY
                and action != WizardMoves.STAY
            ):
                best_value = value
                best_move = action

        return best_move

    def minimax(self, state: GameState, depth: int) -> float:
        if self.is_terminal(state):
            return self.evaluation(state)

        active_entity = state.get_active_entity()

        if isinstance(active_entity, Wizard):
            if depth >= self.max_depth:
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


class WizardAlphaBeta(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        wizard_locs = state.get_all_entity_locations(Wizard)
        if not wizard_locs:
            return -1000000.0

        wizard_loc = wizard_locs[0]
        if isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal):
            return 1000000.0 + 1000.0 * state.score

        portal_loc = state.get_all_tile_locations(Portal)[0]
        goblin_locs = state.get_all_entity_locations(Goblin)

        portal_dist = abs(wizard_loc.row - portal_loc.row) + abs(
            wizard_loc.col - portal_loc.col
        )
        nearest_goblin_dist = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_locs
            )
            if goblin_locs
            else 10.0
        )

        danger_penalty = (
            -500.0 if nearest_goblin_dist <= 1 else (-120.0 if nearest_goblin_dist == 2 else 0.0)
        )
        return 200.0 * state.score - 80.0 * portal_dist + danger_penalty

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)
        #raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        if state.turn >= 36:
            portal_loc = state.get_all_tile_locations(Portal)[0]
            best_move = WizardMoves.STAY
            best_dist = float("inf")
            for action, successor in self.get_successors(state):
                if not isinstance(action, WizardMoves):
                    continue
                wizard_locs = successor.get_all_entity_locations(Wizard)
                if not wizard_locs:
                    continue
                wizard_loc = wizard_locs[0]
                dist = abs(wizard_loc.row - portal_loc.row) + abs(
                    wizard_loc.col - portal_loc.col
                )
                if dist < best_dist or (
                    dist == best_dist
                    and best_move == WizardMoves.STAY
                    and action != WizardMoves.STAY
                ):
                    best_dist = dist
                    best_move = action
            return best_move

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
            if value > best_value or (
                value == best_value
                and best_move == WizardMoves.STAY
                and action != WizardMoves.STAY
            ):
                best_value = value
                best_move = action
            alpha = max(alpha, best_value)

        return best_move


    def alpha_beta_minimax(
        self, state: GameState, depth: int, alpha: float, beta: float
    ) -> float:
        if self.is_terminal(state):
            return self.evaluation(state)

        active_entity = state.get_active_entity()

        if isinstance(active_entity, Wizard):
            if depth >= self.max_depth:
                return self.evaluation(state)

            successors = list(self.get_successors(state))
            if not successors:
                return self.evaluation(state)

            successors.sort(key=lambda x: self.evaluation(x[1]), reverse=True)

            value = float("-inf")
            for _, successor in successors:
                value = max(
                    value,
                    self.alpha_beta_minimax(successor, depth + 1, alpha, beta),
                )
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        successors = list(self.get_successors(state))
        if not successors:
            return self.evaluation(state)

        successors.sort(key=lambda x: self.evaluation(x[1]))
        value = float("inf")
        for _, successor in successors:
            value = min(value, self.alpha_beta_minimax(successor, depth, alpha, beta))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value




class WizardExpectimax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        wizard_locs = state.get_all_entity_locations(Wizard)
        if not wizard_locs:
            return -1000000.0

        wizard_loc = wizard_locs[0]
        if isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal):
            return 1000000.0 + 1000.0 * state.score

        portal_loc = state.get_all_tile_locations(Portal)[0]
        goblin_locs = state.get_all_entity_locations(Goblin)

        portal_dist = abs(wizard_loc.row - portal_loc.row) + abs(
            wizard_loc.col - portal_loc.col
        )
        nearest_goblin_dist = (
            min(
                abs(wizard_loc.row - g.row) + abs(wizard_loc.col - g.col)
                for g in goblin_locs
            )
            if goblin_locs
            else 10.0
        )

        danger_penalty = (
            -500.0 if nearest_goblin_dist <= 1 else (-120.0 if nearest_goblin_dist == 2 else 0.0)
        )
        return 200.0 * state.score - 80.0 * portal_dist + danger_penalty

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        wizard_loc = state.get_all_entity_locations(Wizard)
        if not wizard_loc:
            return True
        wizard_loc = wizard_loc[0]
        return isinstance(state.tile_grid[wizard_loc.row][wizard_loc.col], Portal)
        #raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        if state.turn >= 40:
            portal_loc = state.get_all_tile_locations(Portal)[0]
            best_move = WizardMoves.STAY
            best_dist = float("inf")
            for action, successor in self.get_successors(state):
                if not isinstance(action, WizardMoves):
                    continue
                wizard_locs = successor.get_all_entity_locations(Wizard)
                if not wizard_locs:
                    continue
                wizard_loc = wizard_locs[0]
                dist = abs(wizard_loc.row - portal_loc.row) + abs(
                    wizard_loc.col - portal_loc.col
                )
                if dist < best_dist or (
                    dist == best_dist
                    and best_move == WizardMoves.STAY
                    and action != WizardMoves.STAY
                ):
                    best_dist = dist
                    best_move = action
            return best_move

        best_move = WizardMoves.STAY
        best_value = float("-inf")

        for action, successor in self.get_successors(state):
            if not isinstance(action, WizardMoves):
                continue
            value = self.expectimax(successor, 1)
            if value > best_value or (
                value == best_value
                and best_move == WizardMoves.STAY
                and action != WizardMoves.STAY
            ):
                best_value = value
                best_move = action

        return best_move


    def expectimax(self, state: GameState, depth: int) -> float:
        if self.is_terminal(state):
            return self.evaluation(state)

        active_entity = state.get_active_entity()

        if isinstance(active_entity, Wizard):
            if depth >= self.max_depth:
                return self.evaluation(state)

            successors = self.get_successors(state)
            if not successors:
                return self.evaluation(state)

            value = float("-inf")
            for _, successor in successors:
                value = max(value, self.expectimax(successor, depth + 1))
            return value

        successors = self.get_successors(state)
        if not successors:
            return self.evaluation(state)

        total_value = 0.0
        for _, successor in successors:
            total_value += self.expectimax(successor, depth)
        return total_value / len(successors)
