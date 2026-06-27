# AGENTS.md

## Project Overview

`mini-agent` is a Python command-line learning project for understanding agent internals. It implements its own Agent Loop, tool calling, memory, local skills, and MCP integration while using the official OpenAI Python SDK for Chat Completions.

## Environment

- Use Python 3.10+; the local development environment currently uses Python 3.12 in `.venv`.
- Install dependencies with:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- Run the CLI with:

```bash
.venv/bin/miniagent
```

## Verification

Before committing code changes, run:

```bash
.venv/bin/python -m pytest
```

For syntax-only verification:

```bash
.venv/bin/python -m compileall src tests
```

## Coding Guidelines

- Keep comments, docstrings, and non-README documentation in English.
- `README.md` is Chinese by default; `README.en.md` is the English version.
- Do not use LangChain, AutoGen, CrewAI, or other agent frameworks.
- Do not use the OpenAI Responses API; this project targets Chat Completions only.
- Keep Agent Loop, Tool Registry, built-in tools, memory, and skill loading implemented locally.
- Prefer small, explicit modules over broad abstractions.
- Keep tool behavior structured and safe by default.

## Commenting Guidelines

- Prefer docstrings for modules, classes, public functions, and important internal helpers.
- Add comments for complex logic, key algorithms, safety decisions, and non-obvious design tradeoffs.
- Keep comments concise, but allow multi-line docstrings when they explain why a design exists.
- Do not comment simple assignments, obvious control flow, or self-explanatory code.
- Inline comments should be rare and used only when a nearby explanation is clearer than a docstring.

## Tool And Skill Rules

- Built-in tools are registered through `src/miniagent/tools`.
- Do not add `list_files`; file discovery should use `search_text` or restricted `run_shell`.
- `run_shell` is synchronous in v1.
- Keep file operations scoped to `workspace_root`.
- Local skills live under `skills/*/SKILL.md`.
- Skill discovery should expose only `name` and `description` by default.
- Full skill instructions and references must be loaded progressively through `load_skill`.

## Security And Secrets

- Never commit API keys, tokens, or real credentials.
- Use environment variables for provider configuration:

```bash
export MINIAGENT_BASE_URL="https://api.deepseek.com"
export MINIAGENT_MODEL="deepseek-v4-pro"
export MINIAGENT_API_KEY="..."
```

- Do not write secrets into README examples beyond placeholders.
- `.venv`, caches, and `__pycache__` are intentionally ignored.

## Git

- Keep commits focused and run tests before committing.
- Do not push unless explicitly asked.
