
# MCP Bolt Proxy Agent

This agent acts as a proxy between a Large Language Model (LLM) and the [Bolt.diy application](https://github.com/stackblitz-labs/bolt.diy).

## Purpose

The primary purpose of this agent is to:
- Receive requests from an LLM.
- Forward these requests to the Bolt.diy application's API.
- Receive responses from Bolt.diy.
- Return the responses back to the LLM.

This allows the LLM to interact with and leverage the functionalities exposed by the Bolt.diy application.

## Configuration

The `mcp_agent.config.yaml` file contains general configuration for the agent, such as the `bolt_api_url`.

The `mcp_agent.secrets.yaml` (created from `mcp_agent.secrets.yaml.example`) should contain any sensitive information, such as API keys for the Bolt.diy application, if required.

## Development

The core logic for handling messages and interacting with the Bolt.diy API is located in `main.py`. You will need to implement the actual HTTP requests to the Bolt.diy application within the `handle_message` method. Consider using a library like `httpx` for asynchronous HTTP requests.

## Installation

To run this agent, ensure you have the necessary dependencies installed. You can install them using pip:

```bash
pip install -r requirements.txt
```
