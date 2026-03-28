# Scrawl

**Write Scratch 3.0 projects as text.**

Scrawl is a CLI toolkit that lets you create, inspect, modify, and compile Scratch 3.0 (`.sb3`) projects — without ever opening the Scratch editor. Write your scripts in plain text `.scr` files and compile them into fully valid `.sb3` projects.

## Quick Start

```bash
# Install
pip install -e .

# Create a new project from scratch
scrawl init game.sb3 --sprite Cat --script Stage main.scr

# Inspect an existing project
scrawl info game.sb3
scrawl sprites game.sb3
scrawl blocks game.sb3

# Compile a script into an existing project
scrawl compile script.scr game.sb3 --target Cat

# Validate project integrity
scrawl validate game.sb3
```

## The `.scr` Language

Write Scratch blocks as readable text:

```
when flag clicked
set [score v] to (0)
forever
  move (10) steps
  if on edge, bounce
  if <(score) > (100)> then
    say [You win!] for (2) seconds
    stop [all v]
  end
  change [score v] by (1)
end
```

Custom blocks:

```
define greet (name)
  say (name) for (2) seconds
end

when flag clicked
greet [World]
```

## Commands

| Command | Description |
|---------|-------------|
| `scrawl init` | Create a new project from scratch |
| `scrawl compile` | Compile `.scr` script into a project |
| `scrawl info` | Show project summary |
| `scrawl sprites` | List all sprites |
| `scrawl variables` | List variables and lists |
| `scrawl blocks` | Show block statistics |
| `scrawl assets` | List referenced assets |
| `scrawl tree` | Show project structure |
| `scrawl validate` | Check project integrity |
| `scrawl pack` | Create `.sb3` from directory |
| `scrawl unpack` | Extract `.sb3` to directory |
| `scrawl rename-sprite` | Rename a sprite |
| `scrawl rename-variable` | Rename a variable or list |
| `scrawl delete-sprite` | Delete a sprite |
| `scrawl set-meta` | Edit metadata fields |

## Block Coverage

132 block definitions covering all standard Scratch 3.0 categories:

- **Events** — flag clicked, sprite clicked, key pressed, broadcast
- **Motion** — move, turn, go to, glide, bounce, set position
- **Looks** — say, think, show/hide, costume, backdrop, effects, size, layers
- **Sound** — play, stop, volume, effects
- **Control** — wait, repeat, forever, if/else, stop, clones
- **Sensing** — touching, mouse, keyboard, timer, ask, distance
- **Operators** — math, comparison, logic, string, random
- **Data** — variables, lists
- **Pen** — pen up/down, color, size, stamp, clear
- **Music** — drums, instruments, tempo

Plus full custom block support (define + call with `%s` and `%b` arguments).

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (297 tests)
pytest

# Run with verbose output
pytest -v
```

## License

MIT
