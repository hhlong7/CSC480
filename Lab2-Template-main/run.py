from agents import (
    WizardAgent,
)
from model import  Wizard
import pyglet

from part2Agents import ( PuzzleWizard, SpellCastingPuzzleWizard,
)


from game import PuzzleGame
import argparse


parser = argparse.ArgumentParser()


parser.add_argument(
    "--agent",
    type=str,
    default="simple",
    help="Puzzle Solving Agents: simple, spell",
)

parser.add_argument("--map", type=str, default="masyu1", help="Map name")


parser.add_argument("--speed", type=float, default=10, help="Moves per second")
parser.add_argument(
    "--depth", type=int, default=4, help="Maximum search depth for reasoning agents"
)

parser.add_argument(
    "--timeout", type=int, default=60, help="Maximum time (seconds) to run"
)

parser.add_argument(
    "--no_render", action="store_true", help="Whether to not render search nodes"
)
parser.add_argument("--debug", action="store_true", help="Enable debug output")
args = parser.parse_args()

available_agents = {
    "simple": PuzzleWizard,
    "spell": SpellCastingPuzzleWizard,
}


if __name__ == "__main__":
    game = PuzzleGame(
        path=f"maps/{args.map}",
        game_tick_interval=1.0 / args.speed,
        no_render=args.no_render,
        debug=args.debug,
        timeout=args.timeout,
    )

    for _ in game.state.get_all_entity_locations(Wizard):
        agent = available_agents[args.agent](game.state)
        game.register_next_wizard_agent(agent)

    game.run()

    if not args.no_render:
        pyglet.app.run()
