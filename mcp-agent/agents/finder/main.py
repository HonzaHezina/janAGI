from mcp_agent.agents.agent import Agent

def find_files(query: str) -> str:
    """
    A placeholder function for the finder agent.
    In a real implementation, this would search the filesystem.
    """
    return f"Placeholder: Would search for files matching '{query}'."

def get_agent() -> Agent:
    """
    Creates and returns the finder agent.
    """
    return Agent(
        name="finder",
        instruction="You are a helpful agent that can find files on the filesystem.",
        functions=[find_files],
        # This agent would typically need access to the 'filesystem' server
        # server_names=["filesystem"],
    )

if __name__ == "__main__":
    finder_agent = get_agent()
    print(f"Agent '{finder_agent.name}' created.")
    print(f"Instruction: {finder_agent.instruction}")
    
    # To test the function directly:
    print("\nTesting the find_files function...")
    result = find_files("report.docx")
    print(result)
