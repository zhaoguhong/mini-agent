# mini-agent

`mini-agent` 是一个用于学习 Agent 实现原理的 Python 命令行项目。主命令是 `miniagent`，直接运行后进入交互式对话。

项目目标是功能完整但不过度复杂：自己实现 Agent Loop、Tool Calling、Memory、Skill 加载和安全限制，同时使用 OpenAI 官方 Python SDK 调用 Chat Completions 标准协议。

## 特性

- 使用 OpenAI 官方 SDK。
- 只调用 `/v1/chat/completions`，不使用 Responses API。
- 支持 OpenAI 兼容服务，例如 DeepSeek。
- 支持流式和非流式响应。
- 默认渲染 Markdown 回复。
- 支持 `/` 开头的交互命令。
- 支持 Session Memory 和 Persistent Memory。
- 支持内置工具：读文件、写文件、局部编辑、文本搜索、同步 Shell、加载 Skill。
- 支持本地 Skill：`skills/*/SKILL.md`。
- 支持 stdio MCP server 配置。

## 安装

需要 Python 3.10+。如果系统 Python 版本较低，建议安装 Python 3.12 后再创建虚拟环境。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 主要依赖

| 库 | 用途 |
| --- | --- |
| `openai` | 官方 SDK，用于调用 Chat Completions |
| `typer` | CLI 子命令和参数解析 |
| `rich` | 终端输出、表格和确认提示 |
| `mcp` | 连接 stdio MCP server |
| `tomli` | Python 3.10 读取 TOML 配置 |

Agent Loop、Tool Registry、内置工具、Memory、Skill 加载和 Skill 引用文件解析都由项目自己实现。

## 配置

配置优先级：

```text
CLI 参数 > 环境变量 > 配置文件 > 默认值
```

默认配置文件：

```text
~/.miniagent/config.toml
```

必填配置：

| 配置项 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `api_key` | `MINIAGENT_API_KEY` | 无 | OpenAI 或兼容服务 API key |
| `model` | `MINIAGENT_MODEL` | 无 | Chat Completions 模型名 |

常用可选配置：

| 配置项 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `base_url` | `MINIAGENT_BASE_URL` | OpenAI SDK 默认值 | OpenAI 兼容 API 地址 |
| `default_language` | `MINIAGENT_DEFAULT_LANGUAGE` | `zh-CN` | 默认回答语言 |
| `stream` | `MINIAGENT_STREAM` | `true` | 是否默认流式输出 |
| `render_markdown` | `MINIAGENT_RENDER_MARKDOWN` | `true` | 是否渲染助手回复中的 Markdown |
| `temperature` | `MINIAGENT_TEMPERATURE` | `0.2` | 采样温度 |
| `max_iterations` | `MINIAGENT_MAX_ITERATIONS` | `8` | 单次请求最大 Agent Loop 次数 |
| `workspace_root` | `MINIAGENT_WORKSPACE` | 当前目录 | 文件和 Shell 工具工作区 |
| `skills_dir` | `MINIAGENT_SKILLS_DIR` | `./skills` | Skill 目录 |
| `tool_timeout` | `MINIAGENT_TOOL_TIMEOUT` | `30` | 普通工具超时，单位秒 |
| `shell_timeout` | `MINIAGENT_SHELL_TIMEOUT` | `60` | Shell 工具超时，单位秒 |
| `require_shell_confirmation` | `MINIAGENT_REQUIRE_SHELL_CONFIRMATION` | `false` | 是否所有 Shell 命令都需要确认；默认仅敏感命令确认 |
| `mcp_enabled` | `MINIAGENT_MCP_ENABLED` | `false` | 是否启用 MCP |
| `mcp_config_path` | `MINIAGENT_MCP_CONFIG` | `~/.miniagent/mcp.json` | MCP 配置文件 |

DeepSeek 示例：

```bash
export MINIAGENT_BASE_URL="https://api.deepseek.com"
export MINIAGENT_MODEL="deepseek-v4-pro"
export MINIAGENT_API_KEY="..."
miniagent
miniagent --language en
miniagent --no-markdown
```

不要把真实 API key 写入仓库。

## CLI

启动交互模式：

```bash
miniagent
```

一次性执行任务：

```bash
miniagent run "Explain this project"
```

查看配置、工具、Skill 和 MCP：

```bash
miniagent config show
miniagent tools list
miniagent skills list
miniagent mcp list
```

交互模式支持：

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

## Agent Loop

每次普通输入会进入 Agent Loop：

1. 加载配置、会话记忆、持久记忆、内置工具、Skill 索引和 MCP 工具。
2. 组装系统提示词、持久记忆摘要、Skill 索引、会话历史和用户输入。
3. 调用 Chat Completions。
4. 如果模型返回普通文本，输出并保存到会话。
5. 如果模型返回 tool calls，校验并执行工具。
6. 把工具结果作为 `role="tool"` 消息写回上下文。
7. 继续循环，直到模型返回最终文本或达到 `max_iterations`。

流式模式下，普通文本会边生成边输出；流式 tool calls 会先累积完整参数，再执行工具。

默认回答语言由 `default_language` 控制，默认是 `zh-CN`。模型会优先遵循用户在当前消息中的明确语言要求；代码、命令、文件路径和工具输出默认保持原样。

助手回复默认使用 Rich 渲染 Markdown。流式模式下会刷新同一个 Markdown 面板；如果需要查看原始 Markdown，可以使用 `/markdown off` 或 `--no-markdown`。

## Tool 加载逻辑

内置工具数量较少，默认全部注册并暴露给模型：

| 工具 | 作用 |
| --- | --- |
| `read_file` | 读取工作区内文本文件 |
| `write_file` | 创建或整体覆盖文件 |
| `edit_file` | 精确替换已有文件中的一段文本 |
| `search_text` | 在工作区搜索文本或正则 |
| `run_shell` | 同步执行受限 Shell 命令 |
| `load_skill` | 按需加载 Skill 正文或引用文件 |

不提供 `list_files`。文件探索通过 `search_text` 和受限 `run_shell` 完成。

写文件和编辑文件不需要确认，但始终限制在 `workspace_root` 内。Shell 工具默认允许常见只读命令直接执行；会修改文件、改变 Git 状态、安装依赖、执行网络脚本等敏感命令需要确认；明显危险的命令会直接拒绝。没有确认回调时，敏感 Shell 命令默认拒绝。

## Skill 加载逻辑

Skill 是渐进式披露：

- 启动时只扫描 `skills/*/SKILL.md`。
- 默认只向模型暴露 `name` 和 `description`。
- 不默认注入正文、`triggers` 或 `references`。
- 模型判断 Skill 可能有用时，调用 `load_skill`。
- 第一次 `load_skill` 返回 metadata、正文和引用文件列表。
- 需要示例或补充资料时，再调用 `load_skill` 加载指定 reference。

示例 Skill 位于：

```text
skills/python-tutor/
├── SKILL.md
└── references/
    ├── beginner-project.md
    └── code-review-checklist.md
```

引用文件必须位于对应 Skill 目录内，不能通过 `../` 访问外部路径。

## MCP

v1 支持 stdio MCP server。默认关闭：

```bash
export MINIAGENT_MCP_ENABLED=true
```

配置文件示例：

```json
{
  "servers": {
    "filesystem": {
      "transport": "stdio",
      "command": "mcp-server-filesystem",
      "args": ["/path/to/workspace"],
      "env": {}
    }
  }
}
```

MCP 工具会转换成 Chat Completions tools schema，并注册到统一 Tool Registry。

## 开发

```bash
python -m compileall src
python -m pytest
```

所有代码注释和除 `README.md` 外的文档使用英文。
