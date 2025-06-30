# MCP aggregator example

This example shows connecting to multiple MCP servers via the MCPAggregator interface. An MCP aggregator will combine multiple MCP servers into a single interface allowing users to bypass limitations around the number of MCP servers in use.

```plaintext
┌────────────┐      ┌──────────────┐
│ Aggregator │──┬──▶│  Fetch       │
└────────────┘  │   │  MCP Server  │
                │   └──────────────┘
                |   ┌──────────────┐
                └──▶│  Filesystem  │
                    │  MCP Server  │
                    └──────────────┘
```

## `1` App set up

First, clone the repo and navigate to the basic‑agent example:

```bash
git clone https://github.com/lastmile-ai/mcp-agent.git
cd mcp-agent/examples/basic/mcp_server_aggregator
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

## `2` Set up secrets and environment variables

Copy and configure your env variables:

```bash
cp mcp_agent.secrets.yaml.example mcp_agent.secrets.yaml
```

Then open `mcp_agent.secrets.yaml` and add your api key for your preferred LLM.

## `3` Run locally

Run your MCP Agent app:

```bash
uv run main.py
```
