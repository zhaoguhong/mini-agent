# mini-agent

`mini-agent` is a small Python command-line project for learning how agents work. The main command is `miniagent`; running it without subcommands starts an interactive chat session.

The project uses the official OpenAI Python SDK with the Chat Completions `/v1/chat/completions` protocol only. It does not use the Responses API, LangChain, AutoGen, or another agent framework.

## Features

- Official OpenAI Python SDK.
- Chat Completions only.
- OpenAI-compatible providers such as DeepSeek.
- Streaming and non-streaming responses.
- Markdown rendering by default.
- Claude-Code-style slash commands.
- Session and persistent memory.
- Built-in tools for file reading, file writing, exact file edits, text search, synchronous shell commands, and skill loading.
- Local skills from `skills/*/SKILL.md`.
- Configurable stdio MCP servers.

## Install

Python 3.10+ is required. If the system Python is older, install Python 3.12 before creating the virtual environment.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Main Dependencies

| Package | Purpose |
| --- | --- |
| `openai` | Official SDK for Chat Completions |
| `typer` | CLI commands and options |
| `rich` | Terminal output, tables, and confirmations |
| `mcp` | stdio MCP server integration |
| `tomli` | TOML reading on Python 3.10 |

The Agent Loop, Tool Registry, built-in tools, memory, skill loading, and skill reference parsing are implemented by this project.

## Configure

Precedence:

```text
CLI args > environment variables > config file > defaults
```

Default config file:

```text
~/.miniagent/config.toml
```

Required config:

| Key | Env var | Default | Description |
| --- | --- | --- | --- |
| `api_key` | `MINIAGENT_API_KEY` | none | API key |
| `model` | `MINIAGENT_MODEL` | none | Chat Completions model name |

Common optional config:

| Key | Env var | Default | Description |
| --- | --- | --- | --- |
| `base_url` | `MINIAGENT_BASE_URL` | OpenAI SDK default | OpenAI-compatible base URL |
| `default_language` | `MINIAGENT_DEFAULT_LANGUAGE` | `zh-CN` | Default response language |
| `stream` | `MINIAGENT_STREAM` | `true` | Stream output by default |
| `render_markdown` | `MINIAGENT_RENDER_MARKDOWN` | `true` | Render assistant Markdown output |
| `temperature` | `MINIAGENT_TEMPERATURE` | `0.2` | Sampling temperature |
| `max_iterations` | `MINIAGENT_MAX_ITERATIONS` | `8` | Max loop iterations per task |
| `workspace_root` | `MINIAGENT_WORKSPACE` | current directory | Tool workspace |
| `skills_dir` | `MINIAGENT_SKILLS_DIR` | `./skills` | Skill directory |
| `tool_timeout` | `MINIAGENT_TOOL_TIMEOUT` | `30` | General tool timeout in seconds |
| `shell_timeout` | `MINIAGENT_SHELL_TIMEOUT` | `60` | Shell timeout in seconds |
| `require_shell_confirmation` | `MINIAGENT_REQUIRE_SHELL_CONFIRMATION` | `false` | Require confirmation for every shell command; by default only sensitive commands ask |
| `mcp_enabled` | `MINIAGENT_MCP_ENABLED` | `false` | Enable MCP tools |
| `mcp_config_path` | `MINIAGENT_MCP_CONFIG` | `~/.miniagent/mcp.json` | MCP config path |

## Usage

```bash
miniagent
miniagent --language en
miniagent --no-markdown
miniagent run "Explain this project"
miniagent config show
miniagent tools list
miniagent skills list
miniagent mcp list
```

Interactive slash commands:

```text
/help
/exit
/clear
/model
/model <name>
/language
/language <code>
/config
/tools
/skills
/mcp
/memory
/save
/new
/stream on
/stream off
/markdown on
/markdown off
```

`default_language` controls the default answer language. The model should follow explicit per-turn language requests from the user, while code, commands, file paths, and tool output stay unchanged unless translation is requested.

Assistant replies are rendered as Markdown with Rich by default. Streaming mode refreshes one Markdown panel; use `/markdown off` or `--no-markdown` to inspect raw Markdown.

## Tools

Built-in tools are small enough to be registered and exposed by default:

| Tool | Purpose |
| --- | --- |
| `read_file` | Read a text file inside the workspace |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace an exact text segment in a file |
| `search_text` | Search workspace files by text or regex |
| `run_shell` | Run a restricted synchronous shell command |
| `load_skill` | Load skill instructions or a resource file |

There is no `list_files` tool. File discovery is handled by `search_text` and restricted `run_shell`.

File writes and edits do not ask for confirmation, but they are always limited to `workspace_root`. The shell tool allows common read-only commands without confirmation; commands that modify files, change Git state, install dependencies, or execute network scripts ask for confirmation; clearly dangerous commands are denied. Without a confirmation callback, sensitive shell commands are denied.

## Skills

Skills use progressive disclosure:

- Startup scans `skills/*/SKILL.md`.
- Only `name` and `description` are exposed by default.
- Full instructions and available resource paths are returned by `load_skill`.
- Resource files are loaded only when explicitly requested through `load_skill` with `resource`.

Resources are discovered from `references/`, `reference/`, `docs/`, `examples/`, `assets/`, `resources/`, `templates/`, and `snippets/`. A resource request must use the full relative path shown in `available resources`.

The repository includes `skills/python-tutor` as an example skill with resource files.

## MCP

v1 supports stdio MCP servers. MCP tools are adapted into the same Tool Registry used by built-in tools.
