import os
import requests
from mcp_agent.agents.agent import Agent

# This key should be securely managed, e.g., via environment variables
# For demonstration, it's left as a placeholder.
HF_TOKEN = os.environ.get("HF_TOKEN", "Bearer YOUR_HF_TOKEN")

def generate_image_from_prompt(prompt: str = "a cat in a hat") -> str:
    """
    Generates an image using the Stable Diffusion model from Hugging Face.

    Args:
        prompt: The text prompt to generate the image from.

    Returns:
        A string containing the URL of the generated image or an error message.
    """
    api_url = "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
    headers = {"Authorization": HF_TOKEN}
    
    try:
        response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Assuming the response is a binary image
        # If the API returns a JSON with a URL, the logic needs to be adjusted.
        # For example: image_url = response.json().get("generated_image_url")
        # This example will save the image and return its path, which is more tool-like.
        
        # Let's assume the API returns a JSON with a URL as the original script suggested.
        result = response.json()
        if isinstance(result, dict) and "generated_image_url" in result:
             return f"Image generated successfully: {result['generated_image_url']}"
        elif isinstance(result, dict) and 'error' in result:
             return f"API Error: {result['error']}"
        else:
             # Fallback for unexpected response format
             return "Image generated, but URL not found in response."

    except requests.exceptions.RequestException as e:
        return f"Failed to generate image. Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"


def get_agent() -> Agent:
    """
    Creates and returns the image_generator agent.
    """
    return Agent(
        name="image_generator",
        instruction="You are an agent that generates images from text prompts using a Hugging Face model.",
        functions=[generate_image_from_prompt],
    )

if __name__ == "__main__":
    # Example of how to get and use the agent
    image_agent = get_agent()
    print(f"Agent '{image_agent.name}' created.")
    print(f"Instruction: {image_agent.instruction}")
    
    # To test the function directly:
    print("\nTesting the image generation function...")
    # Make sure to set the HF_TOKEN environment variable for this to work
    if "YOUR_HF_TOKEN" in HF_TOKEN:
        print("Skipping test: Hugging Face token not set. Please set the HF_TOKEN environment variable.")
    else:
        result = generate_image_from_prompt("a futuristic city skyline at sunset")
        print(result)