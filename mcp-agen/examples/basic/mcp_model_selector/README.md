# LLM Selector example

This example shows using MCP's ModelPreferences type to select a model (LLM) based on speed, cost and intelligence priorities.

https://github.com/user-attachments/assets/04257ae4-a628-4c25-ace2-6540620cbf8b

---

```plaintext
┌──────────┐      ┌─────────────────────┐
│ Selector │──┬──▶│       gpt-4o        │
└──────────┘  │   └─────────────────────┘
              │   ┌─────────────────────┐
              ├──▶│     gpt-4o-mini     │
              │   └─────────────────────┘
              │   ┌─────────────────────┐
              ├──▶│  claude-3.5-sonnet  │
              │   └─────────────────────┘
              │   ┌─────────────────────┐
              └──▶│   claude-3-haiku    │
                  └─────────────────────┘
```

## `1` App set up

First, clone the repo and navigate to the mcp_model_selector example:

```bash
git clone https://github.com/lastmile-ai/mcp-agent.git
cd mcp-agent/examples/basic/mcp_model_selector
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

## `2` Run locally

Run your MCP Agent app:

```bash
uv run main.py
```

## `2.1` Run locally in Interactive mode

Run your MCP Agent app:

```bash
uv run interactive.py
```
