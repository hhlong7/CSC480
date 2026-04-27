# Lab 2: Riddles in the Dark

In this lab you will learn how to use general purpose logic satisfaction tools to model logical problems to guide agent decisions. Much of the underlying code is similar to Lab 1, although some things have changed and so make sure to keep this lab separate. Make sure all of your code is in `part1Solvers.py` and `part2Agents.py`, and do not import any additional external libraries or change any class or function signatures.  

## Part 0: Setup and Installation

For this lab you will be using the [Z3 SMT Solver](https://github.com/Z3Prover/z3) (and its python bindings `z3-solver`). You will need to install Z3 using pip: `pip install z3-solver`  or through another python package manager such as conda or [uv](https://docs.astral.sh/uv/). Additionally, the rendering for the lab uses `pyglet` which was bundled with the last lab. You can reuse the pyglet python source from lab 1 or install it alongside `z3` with `pip install pyglet`. If you are using uv for python package management this repo also contains the pyproject.toml to quickly sync and run the code.  

## Part 1: Simple Solvers

In this part you will be shown the basic syntax of the Z3 in python, and use it to solve a range of simple logical puzzles. 

Read through `part1Solvers.py` and complete the commented functions. This part is entirely self contained and meant to help get you familiar with Z3 and using SMT to solve various logical problems.

## Part 2: A Song of Ice and Fire

In this part you will use what you learned in part 1 to design a wizard agent to solve complex puzzles in the world. 

### The Masyu Puzzle
Your wizard has found itself in a very strange part of the dungeon dimensions, where old gods rule by strange cultic rituals and rules that you must follow in order to escape. 

In an empty dungeon your wizard finds two different kinds of stones, Fire Stones and Ice Stones. In order to appease the gods you must create a magic circle by walking the wizard around a cycle, passing through every stone, and finishing at your starting location. Your path must never intersect (the floor is decaying and by stepping upon the same tile twice it is likely to crumble into the abyss). 

When after entering a cell with a Fire Stone, instead of getting a good tri-tip sandwich as you would expect, you must make a 90 degree turn from the direction you entered into the cell (i.e. you cannot travel in a continuous straight line through a fire stone cell). However your path must maintain a straight path (i.e. no turns) through both the previous cell visited before the fire stone, and the next cell after the fire stone. 

When after entering a cell with an Ice Stone, you must travel straight through in the direction you entered into the cell (i.e. you cannot turn). However your path must make a 90 degree turn in either the previous cell visited before the fire stone, or the next cell after the fire stone. 

You may note that this is very similar to the puzzle game [Masyu](https://en.wikipedia.org/wiki/Masyu). 


### Puzzle Solving Wizard

Fill in the code for `PuzzleWizard` in `part2Agents.py` so that your wizard can navigate an arbitrary Masyu puzzle. You should use your skills in Z3 that you developed in part 1 to give your wizard powerful reasoning abilities. A hard-coded solution to the map `masyu1` has been included to help you debug.

### Solving Puzzles with Magic

After being able to escape the first puzzle dungeon, you discover that some dungeons have neutral stones that prevent the formation of a magic circle. Luckily, your wizard is equipped with new actions: `WizardSpells.FIREBALL` and `WizardSpells.FREEZE` which can turn any stone into a fire stone or ice stone at the cost of 15 or 10 mana respectively. This allows the wizard to both, solve puzzles with the presence of neutral stones as well as potentially solve impossible puzzles by altering existing stone types. For this part, fill in the code for `SpellCastingPuzzleWizard` to solve these otherwise impossible puzzles while using the _minimum amount of mana possible_.

Hint: This seems like it might actually be a search problem with a logic problem hidden inside of it!
