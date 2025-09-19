from mcp_agent.agents.agent import Agent

def generate_code(task: str) -> str:
    """
    Generates code based on the given task description.
    """
    return f"CodeWriter generated code for: {task}"

def get_agent() -> Agent:
    """
    Creates and returns the codewriter agent.
    """
    return Agent(
        name="codewriter",
        instruction="You are a helpful agent that can generate code based on task descriptions.",
        functions=[generate_code],
    )

if __name__ == "__main__":
    codewriter_agent = get_agent()
    print(f"Agent '{codewriter_agent.name}' created.")
    print(f"Instruction: {codewriter_agent.instruction}")
    
    # To test the function directly:
    print("\nTesting the generate_code function...")
    result = generate_code("Create a Python function that calculates fibonacci numbers")
    print(result)
