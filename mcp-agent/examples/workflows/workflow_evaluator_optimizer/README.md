# Evaluator-Optimizer Workflow example

This example is a job cover letter refinement system, which generates a draft based on job description, company information, and candidate details. Then, the evaluator reviews the letter, provides a quality rating, and offers actionable feedback. The cycle continues until the letter meets a predefined quality standard.

To make things interesting, we specify the company information as a URL, expecting the agent to fetch it using the MCP 'fetch' server, and then using that information to generate the cover letter.

![Evaluator-optimizer workflow (Image credit: Anthropic)](https://www.anthropic.com/_next/image?url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F14f51e6406ccb29e695da48b17017e899a6119c7-2401x1000.png&w=3840&q=75)

---

```plaintext
┌───────────┐      ┌────────────┐
│ Optimizer │─────▶│  Evaluator │──────────────▶
│ Agent     │◀─────│  Agent     │ if(excellent)
└─────┬─────┘      └────────────┘  then out
      │
      ▼
┌────────────┐
│ Fetch      │
│ MCP Server │
└────────────┘
```

## `1` App set up

First, clone the repo and navigate to the workflow evaluator optimizer example:

```bash
git clone https://github.com/lastmile-ai/mcp-agent.git
cd mcp-agent/examples/workflows/workflow_evaluator_optimizer
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

## `2` Set up environment variables

Copy and configure your secrets and env variables:

```bash
cp mcp_agent.secrets.yaml.example mcp_agent.secrets.yaml
```

Then open `mcp_agent.secrets.yaml` and add your api key for your preferred LLM.

## (Optional) Configure tracing

In `mcp_agent.config.yaml`, you can set `otel` to `enabled` to enable OpenTelemetry tracing for the workflow.
You can [run Jaeger locally](https://www.jaegertracing.io/docs/2.5/getting-started/) to view the traces in the Jaeger UI.

## `3` Run locally

Run your MCP Agent app:

```bash
uv run main.py
```
