# Basic MCP Agent example

This MCP Agent app shows a "finder" Agent which has access to the [fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) and [filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) MCP servers.

You can ask it information about local files or URLs, and it will make the determination on what to use at what time to satisfy the request.

## <img width="2160" alt="Image" src="https://github.com/user-attachments/assets/14cbfdf4-306f-486b-9ec1-6576acf0aeb7" />

```plaintext
┌──────────┐      ┌──────────────┐
│  Finder  │──┬──▶│  Fetch       │
│  Agent   │  │   │  MCP Server  │
└──────────┘  │   └──────────────┘
              |   ┌──────────────┐
              └──▶│  Filesystem  │
                  │  MCP Server  │
                  └──────────────┘
```

## `1` App set up

First, clone the repo and navigate to the basic‑agent example:

```bash
git clone https://github.com/lastmile-ai/mcp-agent.git
cd mcp-agent/examples/basic/mcp_basic_agent
```

Install `uv` (if you don’t have it):

```bash
pip install uv
```

Sync `mcp-agent` project dependencies:

```bash
uv sync
```

Install requirements specific to this example:

```bash
uv pip install -r requirements.txt
```

## `2` Set up api keys

In `main.py`, set your `api_key` in `OpenAISettings` and/or `AnthropicSettings`.

## `3` Run locally

Run your MCP Agent app:

```bash
uv run main.py
```
