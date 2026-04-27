from enum import Enum
from typing import Self
from dataclasses import dataclass, replace


@dataclass(frozen=True, eq=True)
class Location:
    row: int
    col: int

    def __lt__(self, other: Self) -> bool:
        if self.row < other.row:
            return True
        elif self.row == other.row:
            return self.col < other.col
        else:
            return False


@dataclass(frozen=True, eq=True)
class MapTile:
    pass


@dataclass(frozen=True, eq=True)
class EmptyTile(MapTile):
    def __str__(self):
        return " "


@dataclass(frozen=True, eq=True)
class Wall(MapTile):
    def __str__(self):
        return "#"

@dataclass(frozen=True, eq=True)
class Stone(MapTile):
    def __str__(self):
        return "F"


@dataclass(frozen=True, eq=True)
class FireStone(Stone):
    def __str__(self):
        return "F"

@dataclass(frozen=True, eq=True)
class IceStone(Stone):
    def __str__(self):
        return "I"

@dataclass(frozen=True, eq=True)
class NeutralStone(Stone):
    def __str__(self):
        return "N"

@dataclass(frozen=True, eq=True)
class Entity:
    id: int = 0

    def __lt__(self, other) -> bool:
        return self.id < other.id


@dataclass(frozen=True, eq=True)
class EmptyEntity(Entity):
    def __str__(self):
        return " "

@dataclass(frozen=True, eq=True)
class Wizard(Entity):
    def __str__(self):
        return "W"

class WizardMoves(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    RIGHT = (0, 1)
    LEFT = (0, -1)
    STAY = (0, 0)


    def __str__(self):
        return f"Wizard {self.name}"

class WizardSpells(Enum):
    FIREBALL = 0
    FREEZE = 1

    def __str__(self):
        return f"Wizard {self.name}"



GameAction = WizardMoves | WizardSpells


@dataclass(frozen=True, eq=True)
class GameState:
    grid_size: tuple[int, int]
    tile_grid: tuple[tuple[MapTile, ...], ...]
    entity_grid: tuple[tuple[Entity, ...], ...]
    active_entity_location: Location
    turn: int = 0
    mana_spent: int =0

    def advance_turn(self) -> Self:
        return replace(self, turn=self.turn + 1)

    def replace_mana(self, new_mana: int) -> Self:
        return replace(self, mana_spent=new_mana)

    def replace_active_entity_location(self, loc: Location) -> Self:
        return replace(self, active_entity_location=loc)

    def replace_entity(self, row: int, col: int, new_entity: Entity) -> Self:
        list_grid = list([list(row) for row in self.entity_grid])
        list_grid[row][col] = new_entity
        return replace(self, entity_grid=tuple((tuple(row) for row in list_grid)))

    def replace_tile(self, row: int, col: int, new_tile: MapTile) -> Self:
        list_grid = list([list(row) for row in self.tile_grid])
        list_grid[row][col] = new_tile
        return replace(self, tile_grid=tuple((tuple(row) for row in list_grid)))

    def get_all_tile_locations(self, type) -> list[Location]:
        locs: list[Location] = []
        for r, row in enumerate(self.tile_grid):
            for c, tile in enumerate(row):
                if isinstance(tile, type):
                    locs.append(Location(row=r, col=c))
        return locs

    def get_all_entity_locations(self, type) -> list[Location]:
        locs: list[Location] = []
        for r, row in enumerate(self.entity_grid):
            for c, entity in enumerate(row):
                if isinstance(entity, type):
                    locs.append(Location(row=r, col=c))
        return locs

    def get_active_entity(self) -> Entity:
        return self.entity_grid[self.active_entity_location.row][
            self.active_entity_location.col
        ]

    def __lt__(self, other: Self) -> bool:
        my_hash = hash(self)
        other_hash = hash(other)
        return my_hash < other_hash

    def __str__(self):
        lines = []
        lines.append("GameState:")
        lines.append(f"Grid Size: {self.grid_size}")
        lines.append(
            f"Active Entity: {repr(self.get_active_entity())} @ {self.active_entity_location}"
        )

        lines.append("\n")

        lines.append(f"Tile Grid: {self.grid_size}")
        tile_grid_lines = []
        tile_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))
        for grid_line in self.tile_grid:
            tile_grid_lines.append(
                " ".join(["|"] + [str(tile) for tile in grid_line] + ["|"])
            )
        tile_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n".join(tile_grid_lines))
        lines.append("\n")

        lines.append(f"Entity Grid: {self.grid_size}")
        entity_grid_lines = []
        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))
        for entity_line in self.entity_grid:
            entity_grid_lines.append(
                " ".join(["|"] + [str(entity) for entity in entity_line] + ["|"])
            )
        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n".join(entity_grid_lines))

        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n")

        return "\n".join(lines)


class GameTransitions:
    def get_successors(source: GameState) -> tuple[tuple[GameAction, GameState], ...]:
        wizard = source.get_active_entity()
        wizard_loc = source.active_entity_location

        if not isinstance(wizard, Wizard):
            raise ValueError(
                f"Tried to calculate wizard action successors for Game State : {source},  with active entity : {wizard}"
            )

        transitions: list[tuple[GameAction, GameState]] = []

        if isinstance(source.tile_grid[wizard_loc.row][wizard_loc.col], Stone):
            transitions.append(
                (
                    WizardSpells.FIREBALL,
                    source.replace_tile(
                        wizard_loc.row, wizard_loc.col, FireStone()
                    ).replace_mana(source.mana_spent + 15),
                )
            )
            transitions.append(
                (
                    WizardSpells.FREEZE,
                    source.replace_tile(
                        wizard_loc.row, wizard_loc.col, IceStone()
                    ).replace_mana(source.mana_spent + 10),
                )
            )

        for action in WizardMoves:
            dir_row, dir_col = action.value
            target = Location(wizard_loc.row + dir_row, wizard_loc.col + dir_col)
            in_bounds = (0 <= target.row < source.grid_size[0]) and (
                0 <= target.col < source.grid_size[1]
            )
            if in_bounds:
                target_tile = source.tile_grid[target.row][target.col]
                target_entity = source.entity_grid[target.row][target.col]
                if action == WizardMoves.STAY:
                    successor = source.advance_turn()
                    transitions.append(
                        (
                            action,
                            successor,
                        )
                    )

                if isinstance(target_tile, EmptyTile):
                    if isinstance(target_entity, EmptyEntity):
                        successor = (
                            (
                                source.replace_entity(
                                    wizard_loc.row, wizard_loc.col, EmptyEntity()
                                )
                                .replace_entity(target.row, target.col, wizard)
                                .replace_active_entity_location(target)
                            )
                            .advance_turn()
                        )
                        transitions.append(
                            (
                                action,
                                successor,
                            )
                        )
                elif isinstance(target_tile, Stone):
                    if isinstance(target_entity, EmptyEntity):
                        successor = (
                            (
                                source.replace_entity(
                                    wizard_loc.row, wizard_loc.col, EmptyEntity()
                                )
                                .replace_entity(target.row, target.col, wizard)
                                .replace_active_entity_location(target)
                            )
                            .advance_turn()
                        )
                        transitions.append(
                            (
                                action,
                                successor,
                            )
                        )
        return tuple(transitions)
