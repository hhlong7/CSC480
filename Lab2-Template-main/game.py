import sys
import time
from enum import Enum
import pyglet
from model import (
    Entity,
    EmptyEntity,
    Wizard,
    GameState,
    WizardMoves,
    GameAction,
    Location,
    MapTile,
    FireStone,
    IceStone,
    Wall,
    EmptyTile,
    GameTransitions, NeutralStone,
)
from agents import (
    EntityAgent,
    WizardAgent,
)


class GameStatus(Enum):
    PLAYING = 1
    SUCCESS = 2
    FAILURE = 3


class PuzzleGame:
    status: GameStatus = GameStatus.PLAYING
    tile_size = 64
    game_tick_interval = 0.2
    debug = False

    entity_agent_map: dict[int, EntityAgent] = {}
    path_locs: list[Location] = []
    no_render = False

    def __init__(
        self,
        path: str,
        game_tick_interval: float,
        no_render: bool,
        debug: bool,
        timeout: int,
    ):
        self.start_time = time.time()
        self.game_tick_interval = game_tick_interval
        self.no_render = no_render
        self.debug = debug
        self.timeout = timeout

        self.status = GameStatus.PLAYING

        with open(path) as f:
            file_rows = f.readlines()
        file_rows = [line.rstrip("\n") for line in file_rows]

        grid_size = (len(file_rows), max(len(row) for row in file_rows))
        tile_grid: list[list[MapTile]] = [
            [EmptyTile() for _ in range(grid_size[1])] for _ in range(grid_size[0])
        ]
        entity_grid: list[list[Entity]] = [
            [EmptyEntity() for _ in range(grid_size[1])] for _ in range(grid_size[0])
        ]

        id_counter = 1
        wizard_loc = None
        for r in range(grid_size[0]):
            for c in range(grid_size[1]):
                code = file_rows[r][c].strip()
                match code:
                    case "W":  # w for wizard
                        entity_grid[r][c] = Wizard(id=id_counter)
                        tile_grid[r][c] = EmptyTile()
                        id_counter += 1
                        wizard_loc = Location(r, c)

                    case "F":  # F for Fire Stone
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = FireStone()

                    case "I":  # I for Ice Stone
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = IceStone()

                    case "N":  # I for Ice Stone
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = NeutralStone()

                    case "#":  # Wall
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Wall()

                    case " ":  # Empty
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = EmptyTile()

        if id_counter == 1:
            raise ValueError("Map has no entities!")
        if not wizard_loc:
            raise ValueError("Map has no wizard!")
        self.state = GameState(
            grid_size=grid_size,
            tile_grid=tuple((tuple(row) for row in tile_grid)),
            entity_grid=tuple((tuple(row) for row in entity_grid)),
            active_entity_location=wizard_loc,
        )
        self.path_locs = [wizard_loc]

        if not self.no_render:
            self.wall_img = pyglet.image.load("assets/wall.png")
            self.wizard_img = pyglet.image.load("assets/robo_wizard.png")
            self.fire_stone_img = pyglet.image.load("assets/fire_stone.png")
            self.ice_stone_img = pyglet.image.load("assets/ice_stone.png")
            self.neutral_stone_img = pyglet.image.load("assets/neutral_stone.png")

            self.ground_img = pyglet.image.load("assets/ground.png")
            self.path_light_img = pyglet.image.load("assets/path_light.png")

            self.batch = pyglet.graphics.Batch()

            self.background = pyglet.graphics.Group(order=0)
            self.foreground = pyglet.graphics.Group(order=1)
            self.effects = pyglet.graphics.Group(order=2)

            self.bg_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.grid_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.entity_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.search_sprites: dict[Location, pyglet.sprite.Sprite] = {}

            self.window = pyglet.window.Window(
                width=(self.state.grid_size[1] * self.tile_size),
                height=(self.state.grid_size[0] * self.tile_size),
                caption="Lab 2: Riddles in the Dark",
                resizable=True,
            )
            self.window.set_icon(self.wizard_img.get_image_data())

            self.window.event

            @self.window.event
            def on_draw() -> None:
                self.window.clear()
                self.batch.draw()

            @self.window.event
            def on_resize(width: int, height: int) -> None:
                grid_rows, grid_cols = self.state.grid_size
                fit_tile_height = height // grid_rows
                fit_tile_width = width // grid_cols
                new_tile_size = min(fit_tile_height, fit_tile_width)
                self.tile_size = new_tile_size

                self.render()

    def register_next_wizard_agent(self, agent: WizardAgent) -> None:
        if getattr(agent, "requires_crystal", False):
            self.require_crystal = True
        wizard_locs = self.state.get_all_entity_locations(Wizard)
        for wizard_loc in wizard_locs:
            wizard = self.state.entity_grid[wizard_loc.row][wizard_loc.col]
            if wizard.id not in self.entity_agent_map:
                self.register_entity_agent(agent, wizard.id)
                agent.id = wizard.id
                return
        raise RuntimeError(
            f"No unassigned wizards to register new agent!{wizard_locs} : {self.entity_agent_map} : {agent} "
        )

    def register_entity_agent(self, agent: EntityAgent, id: int) -> None:
        self.entity_agent_map[id] = agent

    def run(self):
        if self.no_render:
            while True:
                self.update(0)
        else:
            pyglet.clock.schedule_interval(self.update, self.game_tick_interval)

    def update(self, dt: float):
        tick_time = time.time()
        if tick_time - self.start_time > self.timeout:
            self.status = GameStatus.FAILURE
            print(f"Timeout after {int(tick_time - self.start_time)} seconds!")
        match self.status:
            case GameStatus.PLAYING:
                self.game_tick()
            case GameStatus.SUCCESS:
                print(
                    f"Victory! at turn:\t{self.state.turn}\n\tMana Spent:\t{self.state.mana_spent}\n\tTime Taken (s):\t{tick_time - self.start_time: .02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()

            case GameStatus.FAILURE:
                print(
                    f"Defeat! at turn {self.state.turn}\n\tTime Taken (s):\t{tick_time - self.start_time: 0.02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()


    def game_tick(self) -> None:

        active_entity = self.state.get_active_entity()
        if active_entity.id in self.entity_agent_map:
            active_agent = self.entity_agent_map[active_entity.id]
            action = active_agent.react(self.state)
            self.game_update(self.state, action)

            if isinstance(action, WizardMoves):
                self.path_locs.append(self.state.active_entity_location)
            else:

                self.grid_sprites = {}

            # Check for loops, if so fail immediately
            if len(self.path_locs[:-1]) != len(set(self.path_locs[:-1])):
                self.status = GameStatus.FAILURE
                print(
                    "Your wizard visited the same location more than once! The floor crumbled away and your wizard fell to an untimely demise!"
                )
                return

            def inline(loc1:Location,loc2:Location)-> bool:
                return loc1.row == loc2.row or loc1.col == loc2.col

            # Check for if loop formed from starting loc back, check masyu rules where white is fire and black is ice
            if len(self.path_locs)>1 and self.path_locs[0] == self.path_locs[-1]:
                fire_stone_locations = self.state.get_all_tile_locations(FireStone)
                ice_stone_locations = self.state.get_all_tile_locations(IceStone)
                neutral_stone_locations = self.state.get_all_tile_locations(NeutralStone)

                if len(neutral_stone_locations) > 0:
                    self.status = GameStatus.FAILURE
                    print(
                        "Your wizard has formed a circle but not activated all of the stones! This has angered the old gods, and your wizard has been banished to the shadow realm!"
                    )
                    return

                for fire_stone_loc in fire_stone_locations:
                    if fire_stone_loc not in self.path_locs:
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has formed a circle but not activated all of the stones (missing {fire_stone_loc})! This has angered the old gods, and your wizard has been banished to the shadow realm!"
                        )
                        return

                    path = self.path_locs[:-1]
                    path_index = path.index(fire_stone_loc)
                    pre_entry_loc = path[path_index-2 % len(path)]
                    enter_loc = path[(path_index-1) % len(path)]
                    exit_loc = path[(path_index+1) % len(path)]
                    post_exit_loc = path[(path_index+2) % len(path)]

                    if inline(enter_loc, exit_loc):
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has activated a fire stone at {fire_stone_loc} but failed to take a turn! This has angered the fire gods, and your wizard has been set ablaze and melted!"
                        )
                        return
                    elif not (inline(pre_entry_loc,fire_stone_loc) and inline(post_exit_loc,fire_stone_loc)) :
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has activated a fire stone at {fire_stone_loc} but failed to move in a straight line both directly before and directly after! This has angered the fire gods, and your wizard has been set ablaze and melted!"
                        )
                        return
                for ice_stone_loc in ice_stone_locations:
                    if ice_stone_loc not in self.path_locs:
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has formed a circle but not activated all of the stones (missing {ice_stone_loc})! This has angered the old gods, and your wizard has been banished to the shadow realm!"
                        )
                        return

                    path = self.path_locs[:-1]
                    path_index = path.index(ice_stone_loc)
                    pre_entry_loc = path[(path_index-2) % len(path)]
                    enter_loc = path[(path_index-1) % len(path)]
                    exit_loc = path[(path_index+1) % len(path)]
                    post_exit_loc = path[(path_index+2) % len(path)]

                    if not inline(enter_loc, exit_loc):
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has activated an ice stone at {ice_stone_loc} but failed to move straight through it! This has angered the ice gods, and your wizard has been frozen and shattered!"
                        )
                        return
                    elif (inline(pre_entry_loc,ice_stone_loc) and inline(post_exit_loc,ice_stone_loc)) :
                        self.status = GameStatus.FAILURE
                        print(
                            f"Your wizard has activated an ice stone at {ice_stone_loc} but failed to take a turn either directly before or after! This has angered the ice gods, and your wizard has been frozen and shattered!"
                        )
                        return

                self.status = GameStatus.SUCCESS
                print(
                    "Your wizard has activated all of the stones and returned to its original location, forming the magic circle to escape!"
                )




        # render game every tick
        self.entity_sprites = {}  # maybe this could be made more efficient, for now assume all entities need to be rerendered each tick
        self.render()

    def render(self) -> None:
        if self.no_render:
            return

        match self.status:
            case GameStatus.PLAYING:
                self.window.set_caption("Lab 2: Riddles in the Dark: PLAYING")
            case GameStatus.SUCCESS:
                self.window.set_caption("Lab 2: Riddles in the Dark: VICTORY")
            case GameStatus.FAILURE:
                self.window.set_caption("Lab 2: Riddles in the Dark: DEFEAT")

        if not self.bg_sprites:
            for r, row in enumerate(self.state.tile_grid):
                for c, tile in enumerate(row):
                    x, y = self.grid_to_pix(r, c)

                    sprite = pyglet.sprite.Sprite(
                        img=self.ground_img,
                        x=x,
                        y=y,
                        batch=self.batch,
                        group=self.background,
                    )
                    sprite.height = self.tile_size
                    sprite.width = self.tile_size
                    self.bg_sprites[Location(r, c)] = sprite

        if not self.grid_sprites:
            for r, row in enumerate(self.state.tile_grid):
                for c, tile in enumerate(row):
                    x, y = self.grid_to_pix(r, c)

                    if isinstance(tile, Wall):
                        sprite = pyglet.sprite.Sprite(
                            img=self.wall_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, IceStone):
                        sprite = pyglet.sprite.Sprite(
                            img=self.ice_stone_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, FireStone):
                        sprite = pyglet.sprite.Sprite(
                            img=self.fire_stone_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, NeutralStone):
                        sprite = pyglet.sprite.Sprite(
                            img=self.neutral_stone_img ,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite

        if not self.entity_sprites:
            for r, row in enumerate(self.state.entity_grid):
                for c, entity in enumerate(row):
                    if isinstance(entity, Wizard):
                        x, y = self.grid_to_pix(r, c)
                        sprite = pyglet.sprite.Sprite(
                            img=self.wizard_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.entity_sprites[Location(r, c)] = sprite

        for location in self.path_locs:
            x, y = self.grid_to_pix(location.row, location.col)
            sprite = pyglet.sprite.Sprite(
                img=self.path_light_img,
                x=x,
                y=y,
                batch=self.batch,
                group=self.effects,
            )
            sprite.height = self.tile_size
            sprite.width = self.tile_size
            self.search_sprites[location] = sprite


    def grid_to_pix(self, row: int, col: int) -> tuple[int, int]:
        return col * self.tile_size, (
            self.state.grid_size[0] - 1 - row
        ) * self.tile_size

    def game_update(self, start_state: GameState, action: GameAction):
        transitions = GameTransitions.get_successors(start_state)
        for (
            transition_action,
            end_state,
        ) in transitions:
            if transition_action == action:
                self.state = end_state
                return

        # if invalid move, make no change
        if self.debug:
            print(f"Illegal move attempted! {action} at state: {start_state}")
