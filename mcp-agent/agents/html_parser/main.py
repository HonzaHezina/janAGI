
from mcp_agent.agents.agent import Agent

def parse_html_from_url(url: str) -> str:
    """
    A placeholder function for the html_parser agent.
    In a real implementation, this would fetch a URL and parse its HTML content.
    """
    return f"Placeholder: Would fetch and parse HTML from '{url}'."

def get_agent() -> Agent:
    """
    Creates and returns the html_parser agent.
    """
    return Agent(
        name="html_parser",
        instruction="You are a helpful agent that can fetch and parse HTML from web pages.",
        functions=[parse_html_from_url],
        # This agent would typically need access to the 'fetch' server
        # server_names=["fetch"],
    )

if __name__ == "__main__":
    parser_agent = get_agent()
    print(f"Agent '{parser_agent.name}' created.")
    print(f"Instruction: {parser_agent.instruction}")

    # To test the function directly:
    print("\nTesting the parse_html_from_url function...")
    result = parse_html_from_url("https://example.com")
    print(result)

