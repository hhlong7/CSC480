import random
from model import (
    GameState,
    GameAction,
    WizardMoves,
    GameTransitions,
    Wizard,
    EmptyEntity,
)
import sys


class EntityAgent:
    id: int

    def react(self, state: GameState) -> GameAction:
        raise NotImplementedError()


class WizardAgent(EntityAgent):
    def __init__(self, initial_state: GameState):
        pass

    def react(self, state: GameState) -> GameAction:
        # given new game state, update any internal state and return next move
        return WizardMoves.STAY
