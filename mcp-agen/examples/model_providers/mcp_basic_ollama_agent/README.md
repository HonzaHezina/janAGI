# MCP Ollama Agent example

This example shows a "finder" Agent using llama models to access the 'fetch' and 'filesystem' MCP servers.

You can ask it information about local files or URLs, and it will make the determination on what to use at what time to satisfy the request.

<img width="2160" alt="Image" src="https://github.com/user-attachments/assets/14cbfdf4-306f-486b-9ec1-6576acf0aeb7" />

## `1` App set up

First, clone the repo and navigate to the MCP Basic Ollama Agent example:

```bash
git clone https://github.com/lastmile-ai/mcp-agent.git
cd mcp-agent/examples/model_providers/mcp_basic_ollama_agent
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

Make sure you have [Ollama installed](https://ollama.com/download). Then pull the required models for the example:

```bash
ollama run llama3.2:3b

ollama run llama3.1:8b
```

## `2` Run locally

Then simply run the example:
`uv run main.py`
