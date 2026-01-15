# Claude Code Instructions for claude-code-queue

This project uses Nix flakes for reproducible builds and development environments.

## ⚠️ CRITICAL: DO NOT USE PIP INSTALL

**IMPORTANT: NEVER run `pip install` in this project.**

This project must be built and tested using Nix only. Do not use pip install, pip install -e ., or any pip commands.

## Development Environment

Always use the Nix development shell for working with this project:

```bash
nix develop
```

## Building and Testing

### Check the flake for errors

```bash
nix flake check
```

### Build the package

```bash
nix build
```

### Run the application

```bash
nix run . -- --help
nix run . -- test
nix run . -- add "example prompt"
```

### Test the built binary directly

After building with `nix build`:

```bash
./result/bin/claude-queue --help
```

## Code Formatting and Linting

Use `nix fmt` for all formatting and linting:

```bash
# Format all code
nix fmt
```

## Python Development

Inside `nix develop`, you can use Python tools for type checking:

```bash
# Type checking
mypy src/

# Run tests (if available)
pytest
```

## Important Notes

- ⚠️ **NEVER use pip install** - The project MUST be built with Nix only
- ⚠️ **DO NOT use pip install in any context** - Not in development, not in CI/CD, never
- All dependencies are managed in `flake.nix` and `pyproject.toml`
- Use `nix build` to build the package
- Use `nix fmt` to format code (configured via treefmt-nix)
- The development shell includes all necessary tools (pytest, mypy)

## Project Structure

- `src/claude_code_queue/` - Main package source code
- `flake.nix` - Nix flake definition with package and dev shell
- `pyproject.toml` - Python project metadata and dependencies
- `requirements.txt` - Python dependencies (also defined in flake.nix)
- `treefmt.nix` - Code formatting configuration

## Testing Changes

When making changes to the code:

1. Enter development environment: `nix develop`
2. Make your changes
3. Format code: `nix fmt`
4. Build with Nix: `nix build`
5. Verify: `./result/bin/claude-queue --help`
6. Check flake: `nix flake check`
