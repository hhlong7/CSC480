import sys
import time
from enum import Enum
import pyglet
from model import (
    Entity,
    EmptyEntity,
    Wizard,
    Goblin,
    Crystal,
    GameState,
    WizardMoves,
    GoblinMoves,
    GameAction,
    Location,
    MapTile,
    Portal,
    Wall,
    EmptyTile,
    GameTransitions,
)
from agents import (
    EntityAgent,
    GoblinAgent,
    WizardAgent,
    WizardSearchAgent,
    ReasoningWizard,
)


class GameStatus(Enum):
    SEARCHING = 0
    PLAYING = 1
    SUCCESS = 2
    FAILURE = 3


class SearchGame:
    status: GameStatus = GameStatus.SEARCHING
    search_turn: int = 0
    tile_size = 64
    game_tick_interval = 0.2
    debug = False

    entity_agent_map: dict[int, EntityAgent] = {}

    require_crystal = False

    no_render = False

    score = 0

    # used for search tracking
    render_search = True
    number_search_expansions = 0
    search_state_map = {}  # map from grid location to the most recent expanded search state with active location at that location

    def __init__(
        self,
        path: str,
        game_tick_interval: float,
        render_search: bool,
        no_render: bool,
        debug: bool,
        timeout: int,
        require_crystal: bool = False,
    ):
        self.start_time = time.time()
        self.game_tick_interval = game_tick_interval
        self.render_search = render_search
        self.no_render = no_render
        self.debug = debug
        self.timeout = timeout
        self.require_crystal = require_crystal

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

                    case "G":  # g for goblin
                        entity_grid[r][c] = Goblin(id=id_counter)
                        tile_grid[r][c] = EmptyTile()
                        id_counter += 1

                    case "C":  # C for crystal
                        entity_grid[r][c] = Crystal()
                        tile_grid[r][c] = EmptyTile()
                        id_counter += 1

                    case "P":  # P for Portal
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Portal()

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

        if not self.no_render:
            self.wall_img = pyglet.image.load("assets/wall.png")
            self.portal_img = pyglet.image.load("assets/portal.png")
            self.wizard_img = pyglet.image.load("assets/robo_wizard.png")
            self.goblin_img = pyglet.image.load("assets/goblin.png")
            self.ground_img = pyglet.image.load("assets/ground.png")
            self.path_light_img = pyglet.image.load("assets/path_light.png")
            self.visited_light_img = pyglet.image.load("assets/visited_light.png")
            self.frontier_light_img = pyglet.image.load("assets/frontier_light.png")
            self.crystal_img = pyglet.image.load("assets/crystal.png")

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
                caption="Lab 1: Dungeon Crawler",
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

    def register_next_goblin_agent(self, agent: GoblinAgent) -> None:
        goblin_locs = self.state.get_all_entity_locations(Goblin)
        for goblin_loc in goblin_locs:
            goblin = self.state.entity_grid[goblin_loc.row][goblin_loc.col]
            if goblin.id not in self.entity_agent_map:
                self.register_entity_agent(agent, goblin.id)
                agent.id = goblin.id
                return
        raise RuntimeError(
            f"No unassigned goblins to register new agent!{goblin_locs} : {self.entity_agent_map} : {agent} "
        )

    def register_entity_agent(self, agent: EntityAgent, id: int) -> None:
        self.entity_agent_map[id] = agent

    def run(self):
        if self.no_render:
            while True:
                self.update(0)
        elif not self.render_search:
            while self.status == GameStatus.SEARCHING:
                self.update(0)

            pyglet.clock.schedule_interval(self.update, 0.2 * self.game_tick_interval)

        else:
            pyglet.clock.schedule_interval(self.update, self.game_tick_interval)

    def update(self, dt: float):
        tick_time = time.time()
        if tick_time - self.start_time > self.timeout:
            self.status = GameStatus.FAILURE
            print(f"Timeout after {int(tick_time - self.start_time)} seconds!")
        match self.status:
            case GameStatus.SEARCHING:
                self.search_tick()
            case GameStatus.PLAYING:
                self.game_tick()
            case GameStatus.SUCCESS:
                print(
                    f"Victory! (Score: {self.score}) at turn:\t{self.state.turn}\n\tNodes Explored:\t{self.number_search_expansions}\n\tTime Taken (s):\t{tick_time - self.start_time: .02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()

            case GameStatus.FAILURE:
                print(
                    f"Defeat! at turn {self.state.turn}\n\tNodes Explored:\t{self.number_search_expansions}\n\tTime Taken (s):\t{tick_time - self.start_time: 0.02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()

    def search_tick(self):
        self.search_turn += 1
        active_entity = self.state.get_active_entity()
        active_agent = self.entity_agent_map[active_entity.id]
        if isinstance(active_agent, WizardSearchAgent):
            search_expansion_node = active_agent.next_search_expansion()

            if search_expansion_node:
                if self.debug and not isinstance(
                    search_expansion_node.get_active_entity(), Wizard
                ):
                    print(
                        f"Attempted to expand search node from non wizard active game state : {search_expansion_node}"
                    )

                if (not self.no_render) and (self.render_search):
                    x, y = self.grid_to_pix(
                        search_expansion_node.active_entity_location.row,
                        search_expansion_node.active_entity_location.col,
                    )
                    sprite = pyglet.sprite.Sprite(
                        img=self.visited_light_img,
                        x=x,
                        y=y,
                        batch=self.batch,
                        group=self.effects,
                    )
                    sprite.height = self.tile_size
                    sprite.width = self.tile_size
                    self.search_sprites[
                        search_expansion_node.active_entity_location
                    ] = sprite

                successors = GameTransitions.get_successors(search_expansion_node)
                self.number_search_expansions += 1
                for action, target in successors:
                    if not isinstance(action, WizardMoves):
                        raise RuntimeError(
                            f"Attempted to run wizard search with non wizard move transition : {action}"
                        )

                    # Wizard search always assumes the wizard just gets unlimited moves
                    # loop next agent until wizard
                    while target.get_active_entity().id != active_entity.id:
                        target = target.advance_to_next_active_entity()

                    active_agent.process_search_expansion(
                        search_expansion_node, target, action
                    )

                    if (not self.no_render) and (self.render_search):
                        if target.active_entity_location in self.search_state_map and (
                            self.search_state_map[target.active_entity_location]
                            == target
                        ):
                            x, y = self.grid_to_pix(
                                target.active_entity_location.row,
                                target.active_entity_location.col,
                            )
                            sprite = pyglet.sprite.Sprite(
                                img=self.visited_light_img,
                                x=x,
                                y=y,
                                batch=self.batch,
                                group=self.effects,
                            )
                            sprite.height = self.tile_size
                            sprite.width = self.tile_size
                            self.search_sprites[target.active_entity_location] = sprite
                        else:
                            x, y = self.grid_to_pix(
                                target.active_entity_location.row,
                                target.active_entity_location.col,
                            )
                            sprite = pyglet.sprite.Sprite(
                                img=self.frontier_light_img,
                                x=x,
                                y=y,
                                batch=self.batch,
                                group=self.effects,
                            )
                            sprite.height = self.tile_size
                            sprite.width = self.tile_size
                            self.search_sprites[target.active_entity_location] = sprite
                            self.search_state_map[target.active_entity_location] = (
                                target
                            )

            else:
                # Search failed! Resuming Game
                if self.debug:
                    print(
                        f"Search failed! for agent {active_agent} at game state {self.state}"
                    )
                self.status = GameStatus.PLAYING

            if self.render_search:
                self.render()

            if active_agent.plan:
                self.status = GameStatus.PLAYING
        else:
            if self.debug:
                print("Tried to run search tick for non search entity!")
            self.state = self.state.advance_to_next_active_entity()

    def game_tick(self) -> None:
        # Reset all search when doing each game tick
        self.search_turn = 0
        self.search_state_map = {}

        active_entity = self.state.get_active_entity()
        if active_entity.id in self.entity_agent_map:
            active_agent = self.entity_agent_map[active_entity.id]
            action = active_agent.react(self.state)
            self.game_update(self.state, action)

            new_active_entity = self.state.get_active_entity()
            new_active_agent = self.entity_agent_map[new_active_entity.id]

            # reset search if planning agent has no plan for next turn
            if isinstance(new_active_agent, WizardSearchAgent) and (
                not new_active_agent.plan
            ):
                if self.debug:
                    print("No plan found, restarting search")
                new_active_agent.start_search(self.state)
                self.status = GameStatus.SEARCHING

            # keep track of node expansions for general purpose reasoning wizards
            if isinstance(new_active_agent, ReasoningWizard):
                self.number_search_expansions = new_active_agent.nodes_expanded

            # check for game victor
            wizard_loc = self.state.active_entity_location
            if isinstance(self.state.tile_grid[wizard_loc.row][wizard_loc.col], Portal) and (not self.require_crystal or len(self.state.get_all_entity_locations(Crystal)) == 0):
                self.score = self.state.score
                self.status = GameStatus.SUCCESS

            # check for failure
            if len(self.state.get_all_entity_locations(Wizard)) == 0:
                self.status = GameStatus.FAILURE
        else:
            # if no agent found for the entity, advance to next agent
            self.state = self.state.advance_to_next_active_entity()

        # render game every tick
        self.entity_sprites = {}  # maybe this could be made more efficient, for now assume all entities need to be rerendered each tick
        self.render()

    def render(self) -> None:
        if self.no_render:
            return

        match self.status:
            case GameStatus.SEARCHING:
                self.window.set_caption("Lab 1: Dungeon Crawler: SEARCHING")
            case GameStatus.PLAYING:
                self.window.set_caption("Lab 1: Dungeon Crawler: PLAYING")
            case GameStatus.SUCCESS:
                self.window.set_caption("Lab 1: Dungeon Crawler: VICTORY")
            case GameStatus.FAILURE:
                self.window.set_caption("Lab 1: Dungeon Crawler: DEFEAT")

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
                    elif isinstance(tile, Portal):
                        sprite = pyglet.sprite.Sprite(
                            img=self.portal_img,
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
                    elif isinstance(entity, Goblin):
                        x, y = self.grid_to_pix(r, c)

                        sprite = pyglet.sprite.Sprite(
                            img=self.goblin_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.entity_sprites[Location(r, c)] = sprite
                    elif isinstance(entity, Crystal):
                        x, y = self.grid_to_pix(r, c)

                        sprite = pyglet.sprite.Sprite(
                            img=self.crystal_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.entity_sprites[Location(r, c)] = sprite

        if self.render_search:
            active_entity = self.state.get_active_entity()
            if active_entity.id in self.entity_agent_map:
                agent = self.entity_agent_map[active_entity.id]

                if isinstance(agent, WizardSearchAgent) and isinstance(
                    active_entity, Wizard
                ):
                    if agent.plan:
                        wizard_loc = self.state.active_entity_location
                        # rerender search each game tick
                        self.search_sprites = {}

                        # calculate plan path cells
                        moves = agent.plan.copy()
                        moves.reverse()  # reverse plan from pop stack order to iteration order

                        # render path, recalculate path each frame
                        path_locs: list[Location] = []
                        path_loc = wizard_loc
                        for move in moves:
                            move_dir_row, move_dir_col = move.value
                            path_row = path_loc.row + move_dir_row
                            path_col = path_loc.col + move_dir_col
                            path_loc = Location(path_row, path_col)
                            path_locs.append(path_loc)
                        for location in path_locs:
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
