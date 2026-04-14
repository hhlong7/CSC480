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
        raise NotImplementedError


class WizardMiniMax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        raise NotImplementedError


    def minimax(self, state: GameState, depth: int):
        # TODO YOUR CODE HERE
        raise NotImplementedError


class WizardAlphaBeta(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        raise NotImplementedError


    def alpha_beta_minimax(self, state: GameState, depth: int):
        # TODO YOUR CODE HERE
        raise NotImplementedError




class WizardExpectimax(ReasoningWizard):
    max_depth: int = 2

    def evaluation(self, state: GameState) -> float:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def is_terminal(self, state: GameState) -> bool:
        # TODO YOUR CODE HERE
        raise NotImplementedError

    def react(self, state: GameState) -> WizardMoves:
        # TODO YOUR CODE HERE
        raise NotImplementedError


    def expectimax(self, state: GameState, depth: int):
        # TODO YOUR CODE HERE
        raise NotImplementedError
