import json
import os
import logging
import base64
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, AsyncGenerator
import httpx
import time
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# This will search for a .env file in the current directory and load it.
if load_dotenv():
    logger.info("Loaded environment variables from .env file.")
else:
    logger.warning("No .env file found. Relying on system environment variables.")

# --- Pydantic Models ---

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = 0.7
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: list = None
    max_tokens: int = 2048
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    logit_bias: dict = None
    user: str = None

# --- Provider Abstraction ---

class LLMProvider(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        yield  # This makes the method an async generator

    def format_to_openai(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": "chatcmpl-proxy",
            "object": "chat.completion",
            "created": 0,
            "model": self.model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": self._extract_content(response)},
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }

    @abstractmethod
    def _extract_content(self, response: Dict[str, Any]) -> str:
        pass

# Add the scripts directory to the Python path to import the generator
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

from tool_generator import generate_diff


# --- Tool Abstraction and Implementation ---

class Tool(ABC):
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass

class ImageGenerationTool(Tool):
    def __init__(self, model_name: str = "stabilityai/stable-diffusion-xl-base-1.0"):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable not set for ImageGenerationTool")
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        prompt = kwargs.get("prompt")
        if not prompt:
            raise ValueError("Prompt is required for image generation")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"inputs": prompt}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.debug(f"Calling Image Generation API with prompt: {prompt}")
                response = await client.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                image_bytes = response.content
                encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Return a structured JSON response
                return {
                    "content": json.dumps({
                        "type": "image",
                        "data": {
                            "base64": encoded_image,
                            "prompt": prompt,
                            "message": f"Successfully generated image for prompt: '{prompt}'"
                        }
                    })
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"Image Generation API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"Image Generation API error: {e.response.text}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during image generation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

class CreateToolScaffold(Tool):
    """
    A simple tool that takes a full JSON specification and returns the
    diffs needed to create the new tool file.
    """
    async def execute(self, **kwargs) -> Dict[str, Any]:
        tool_spec = kwargs.get("spec")
        if not tool_spec or not isinstance(tool_spec, dict):
            raise ValueError("A valid 'spec' dictionary is required.")

        try:
            diffs = generate_diff(tool_spec)
            return {
                "content": json.dumps({
                    "message": "Successfully generated the diff for the new tool.",
                    "diffs": diffs
                })
            }
        except Exception as e:
            logger.error(f"Error during tool scaffold generation: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate tool scaffold: {str(e)}")


# --- Tool Registry ---

class DalleImageGenerationTool(Tool):
    def __init__(self, model_name: str = "dall-e-3"):
        self.api_url = "https://api.openai.com/v1/images/generations"
        self.model_name = model_name

    async def execute(self, **kwargs) -> Dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set for DalleImageGenerationTool")
        prompt = kwargs.get("prompt")
        if not prompt:
            raise ValueError("Prompt is required for DALL-E image generation")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.debug(f"Calling DALL-E API with prompt: {prompt}")
                response = await client.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                response_data = response.json()
                encoded_image = response_data['data'][0]['b64_json']
                
                return {
                    "content": json.dumps({
                        "type": "image",
                        "data": {
                            "base64": encoded_image,
                            "prompt": prompt,
                            "message": f"Successfully generated DALL-E image for prompt: '{prompt}'"
                        }
                    })
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"DALL-E API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"DALL-E API error: {e.response.text}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during DALL-E image generation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

tool_registry = {
    "generate_image": ImageGenerationTool(),
    "generate_image_dalle": DalleImageGenerationTool(),
    "create_tool_scaffold": CreateToolScaffold()
}


# --- Gemini Provider ---

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.api_url_base = "https://generativelanguage.googleapis.com/v1beta/models"

    def _format_messages(self, messages: List[Message]):
        if not messages:
            return []

        formatted_messages = []
        
        current_role = "user" if messages[0].role == "user" else "model"
        current_content = [messages[0].content]

        for msg in messages[1:]:
            new_role = "user" if msg.role == "user" else "model"
            if new_role == current_role:
                current_content.append(msg.content)
            else:
                formatted_messages.append({
                    "role": current_role,
                    "parts": [{"text": "\n\n".join(current_content)}]
                })
                current_role = new_role
                current_content = [msg.content]

        formatted_messages.append({
            "role": current_role,
            "parts": [{"text": "\n\n".join(current_content)}]
        })

        return formatted_messages

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        api_url = f"{self.api_url_base}/{self.model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        data = {
            "contents": self._format_messages(request.messages),
            "generationConfig": {
                "temperature": request.temperature,
                "topP": request.top_p,
                "maxOutputTokens": request.max_tokens
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(api_url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"Gemini API error: {e.response.text}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        api_url = f"{self.api_url_base}/{self.model_name}:streamGenerateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        data = {
            "contents": self._format_messages(request.messages),
            "generationConfig": {
                "temperature": request.temperature,
                "topP": request.top_p,
                "maxOutputTokens": request.max_tokens
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", api_url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        # The Gemini stream is a JSON array. We need to find complete JSON objects within it.
                        start_idx = buffer.find('{')
                        while start_idx != -1:
                            brace_count = 0
                            end_idx = -1
                            for i in range(start_idx, len(buffer)):
                                if buffer[i] == '{':
                                    brace_count += 1
                                elif buffer[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i
                                        break
                            
                            if end_idx != -1:
                                json_str = buffer[start_idx:end_idx+1]
                                buffer = buffer[end_idx+1:]
                                
                                try:
                                    gemini_response = json.loads(json_str)
                                    content = gemini_response.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                                    
                                    if content:
                                        openai_chunk = {
                                            "id": f"chatcmpl-gemini-{os.urandom(8).hex()}",
                                            "object": "chat.completion.chunk",
                                            "created": int(time.time()),
                                            "model": self.model_name,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": content},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(openai_chunk)}\n\n"
                                except (json.JSONDecodeError, KeyError, IndexError) as e:
                                    logger.warning(f"Could not process Gemini stream object: '{json_str}', error: {e}")
                                
                                start_idx = buffer.find('{')
                            else:
                                break
                
                final_chunk = {
                    "id": f"chatcmpl-gemini-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": self.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini API streaming error: {e.response.text}")
                error_message = {
                    "error": {
                        "message": f"Gemini API streaming error: {e.response.text}",
                        "type": "api_error",
                        "param": None,
                        "code": e.response.status_code
                    }
                }
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"An unexpected streaming error occurred: {e}")
                error_message = {
                    "error": {
                        "message": f"An unexpected streaming error occurred: {e}",
                        "type": "server_error",
                        "param": None,
                        "code": "internal_server_error"
                    }
                }
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"


    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            return response['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing Gemini response: {response}, error: {e}")
            return ""

# --- Hugging Face Provider ---

class HuggingFaceProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable not set")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"

    def _format_messages(self, messages: List[Message]):
        # Many HF models expect a single string prompt
        return " ".join([m.content for m in messages])

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "inputs": self._format_messages(request.messages),
            "parameters": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_new_tokens": request.max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Hugging Face API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"Hugging Face API error: {e.response.text}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "inputs": self._format_messages(request.messages),
            "parameters": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_new_tokens": request.max_tokens
            },
            "stream": True
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                async with client.stream("POST", self.api_url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith('data:'):
                            json_str = line[len('data:'):].strip()
                            if not json_str:
                                continue
                            try:
                                chunk = json.loads(json_str)
                                if chunk.get('details') is not None:
                                    continue
                                token_text = chunk.get('token', {}).get('text', '')
                                if not token_text:
                                    continue
                                
                                openai_chunk = {
                                    "id": f"chatcmpl-hf-{os.urandom(8).hex()}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": self.model_name,
                                    "choices": [{
                                        "index": 0,
                                        "delta": {"content": token_text},
                                        "finish_reason": None
                                    }]
                                }
                                yield f"data: {json.dumps(openai_chunk)}\n\n"
                            except json.JSONDecodeError:
                                logger.warning(f"HuggingFace stream: Failed to decode JSON: {json_str}")
                
                final_chunk = {
                    "id": f"chatcmpl-hf-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": self.model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except httpx.HTTPStatusError as e:
                logger.error(f"Hugging Face API streaming error: {e.response.text}")
                error_message = {
                    "error": {
                        "message": f"Hugging Face API streaming error: {e.response.text}",
                        "type": "api_error",
                        "param": None,
                        "code": e.response.status_code
                    }
                }
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"An unexpected streaming error occurred: {e}")
                error_message = {
                    "error": {
                        "message": f"An unexpected streaming error occurred: {e}",
                        "type": "server_error",
                        "param": None,
                        "code": "internal_server_error"
                    }
                }
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"

    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            if isinstance(response, list) and response:
                if 'generated_text' in response[0]:
                    return response[0]['generated_text']
            elif isinstance(response, dict):
                 if 'generated_text' in response:
                    return response['generated_text']
            return str(response)
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing Hugging Face response: {response}, error: {e}")
            return ""

# --- Provider Factory ---

def get_provider(model_name: str) -> LLMProvider:
    if "gemini" in model_name.lower():
        return GeminiProvider(model_name)
    # Default to Hugging Face for other models
    # This is a simple heuristic; a more robust solution might use a config file
    # or a more explicit model naming convention.
    else:
        return HuggingFaceProvider(model_name)

# --- FastAPI App ---

app = FastAPI()

@app.get("/v1/models")
async def get_models():
    # In a real-world scenario, you might fetch this from a config file
    # or an API, but for this example, we'll keep it simple.
    models = [
        {"id": "gemini-1.5-flash", "object": "model", "owned_by": "google"},
        {"id": "mistralai/Mistral-7B-Instruct-v0.2", "object": "model", "owned_by": "huggingface"},
        # Add other supported models here
    ]
    return JSONResponse(content={"data": models, "object": "list"})

async def handle_tool_call(request: ChatCompletionRequest) -> JSONResponse | None:
    """
    Checks for and handles a tool call in the user's last message.
    Returns a JSONResponse if a tool is executed, otherwise None.
    """
    if not request.messages or request.messages[-1].role != "user":
        return None

    last_message_content = request.messages[-1].content
    try:
        tool_call_data = json.loads(last_message_content)
        if not (isinstance(tool_call_data, dict) and "tool_call" in tool_call_data):
            return None

        tool_call = tool_call_data["tool_call"]
        tool_name = tool_call.get("name")
        tool_arguments = tool_call.get("arguments", {})

        if tool_name not in tool_registry:
            logger.warning(f"Tool '{tool_name}' not found in registry.")
            return None

        logger.info(f"Executing tool: {tool_name} with arguments: {tool_arguments}")
        tool = tool_registry[tool_name]
        
        try:
            tool_result = await tool.execute(**tool_arguments)
            response_content = {
                "id": f"chatcmpl-tool-{os.urandom(8).hex()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": f"tool/{tool_name}",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": tool_result.get("content", "Tool executed successfully.")
                    },
                    "logprobs": None,
                    "finish_reason": "tool_calls"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            return JSONResponse(content=response_content)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error executing tool {tool_name}: {str(e)}")

    except json.JSONDecodeError:
        return None # Not a JSON tool call
    except Exception as e:
        logger.error(f"Error processing potential tool call: {e}")
        return None # Fall through to default behavior

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # --- Tool Call Logic ---
    tool_response = await handle_tool_call(request)
    if tool_response:
        return tool_response

    # --- Default LLM Logic ---
    try:
        provider = get_provider(request.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if request.stream:
        async def stream_wrapper():
            # First, check for a tool call
            tool_response = await handle_tool_call(request)
            if tool_response:
                # If a tool is called, we can't stream the result in the same way.
                # We'll send a single event with the tool's output.
                response_data = json.loads(tool_response.body)
                content = response_data["choices"][0]["message"]["content"]
                
                # Create a single chunk for the tool response
                openai_chunk = {
                    "id": response_data["id"],
                    "object": "chat.completion.chunk",
                    "created": response_data["created"],
                    "model": response_data["model"],
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": "tool_calls"
                    }]
                }
                yield f"data: {json.dumps(openai_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                return

            # If no tool call, proceed with the provider's streaming
            async for chunk in provider.stream_generate(request):
                yield chunk

        return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
    else:
        llm_response = await provider.generate(request)
        openai_formatted_response = provider.format_to_openai(llm_response)
        return JSONResponse(content=openai_formatted_response)

if __name__ == "__main__":
    import uvicorn
    # Ensure you have GEMINI_API_KEY and/or HUGGINGFACE_API_KEY set in your environment
    # e.g., export GEMINI_API_KEY='your_key_here'
    uvicorn.run(app, host="0.0.0.0", port=8000)
