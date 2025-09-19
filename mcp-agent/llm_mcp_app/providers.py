"""
LLM Provider implementations for MCP Agent.
"""

import os
import abc
import json
import time
from typing import Dict, Any, AsyncGenerator, List
import httpx
from fastapi import HTTPException

try:
    from .models import ChatCompletionRequest, Message
    from .config import (logger, GEMINI_API_BASE, HUGGINGFACE_API_BASE, OPENAI_API_BASE,
                        GEMINI_API_KEY, HUGGINGFACE_API_KEY, OPENAI_API_KEY)
except ImportError:
    from models import ChatCompletionRequest, Message
    from config import (logger, GEMINI_API_BASE, HUGGINGFACE_API_BASE, OPENAI_API_BASE,
                       GEMINI_API_KEY, HUGGINGFACE_API_KEY, OPENAI_API_KEY)


class LLMProvider(abc.ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abc.abstractmethod
    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        yield

    async def chat(self, messages: List[Message], max_tokens: int = None, temperature: float = 0.7) -> str:
        """Simple chat method that returns just the content string."""
        request = ChatCompletionRequest(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        response = await self.generate(request)
        return self._extract_content(response)

    def format_to_openai(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": "chatcmpl-proxy",
            "object": "chat.completion",
            "created": int(time.time()),
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
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
            }
        }

    @abc.abstractmethod
    def _extract_content(self, response: Dict[str, Any]) -> str:
        pass


class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.api_url_base = GEMINI_API_BASE

    def _format_messages(self, messages: List[Message]):
        # Simplified message formatting
        return [{"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content}]} for m in messages]

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        api_url = f"{self.api_url_base}/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
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
                response = await client.post(api_url, headers=headers, json=data, timeout=60.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"Gemini API error: {e.response.text}")

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        api_url = f"{self.api_url_base}/{self.model_name}:streamGenerateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
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
                async with client.stream("POST", api_url, headers=headers, json=data, timeout=60.0) as response:
                    response.raise_for_status()
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
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
                                            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
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
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini API streaming error: {e.response.text}")
                error_message = {"error": {"message": f"Gemini API streaming error: {e.response.text}", "type": "api_error", "code": e.response.status_code}}
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"An unexpected streaming error occurred: {e}")
                error_message = {"error": {"message": f"An unexpected streaming error occurred: {e}", "type": "server_error", "code": "internal_server_error"}}
                yield f"data: {json.dumps(error_message)}\n\n"
                yield "data: [DONE]\n\n"

    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            return response['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError, TypeError):
            logger.error(f"Error parsing Gemini response: {response}")
            return ""


class HuggingFaceProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = HUGGINGFACE_API_KEY
        if not self.api_key or self.api_key.startswith("your_"):
            raise ValueError(
                "HUGGINGFACE_API_KEY not properly set. "
                "Get your token from https://huggingface.co/settings/tokens "
                "and set it in .env file as HF_TOKEN=your_actual_token"
            )
        self.api_url = f"{HUGGINGFACE_API_BASE}/{model_name}"

    def _format_messages(self, messages: List[Message]) -> str:
        # Převedeme konverzaci na jeden string prompt
        conversation = ""
        for msg in messages:
            if msg.role == "user":
                conversation += f"Human: {msg.content}\n"
            else:
                conversation += f"Assistant: {msg.content}\n"
        conversation += "Assistant: "
        return conversation

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        prompt = self._format_messages(request.messages)
        data = {
            "inputs": prompt,
            "parameters": {
                "temperature": request.temperature,
                "max_new_tokens": request.max_tokens,
                "return_full_text": False
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"HuggingFace API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"HuggingFace API error: {e.response.text}")

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        # HuggingFace Inference API nepodporuje streaming jednoduše
        # Spustíme normální generate a vrátíme výsledek po částech
        response = await self.generate(request)
        content = self._extract_content(response)
        
        # Simulujeme streaming rozdělením textu
        words = content.split(' ')
        for i, word in enumerate(words):
            chunk = {
                "id": f"chatcmpl-hf-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": self.model_name,
                "choices": [{"index": 0, "delta": {"content": word + " " if i < len(words)-1 else word}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        
        final_chunk = {
            "id": f"chatcmpl-hf-{os.urandom(8).hex()}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": self.model_name,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            if isinstance(response, list) and len(response) > 0:
                return response[0].get('generated_text', '')
            return response.get('generated_text', '')
        except (KeyError, IndexError, TypeError):
            logger.error(f"Error parsing HuggingFace response: {response}")
            return ""


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.api_key = OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.api_url = f"{OPENAI_API_BASE}/chat/completions"

    def _format_messages(self, messages: List[Message]) -> List[Dict]:
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=data, timeout=60.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"OpenAI API error: {e.response.text}")

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stream": True
        }
        
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", self.api_url, headers=headers, json=data, timeout=60.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            yield line + "\n"
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API streaming error: {e.response.text}")
                error_message = {"error": {"message": f"OpenAI API error: {e.response.text}", "type": "api_error"}}
                yield f"data: {json.dumps(error_message)}\n\n"

    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            return response['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            logger.error(f"Error parsing OpenAI response: {response}")
            return ""


def get_provider(model_name: str) -> LLMProvider:
    """Factory function to get the appropriate LLM provider."""
    # Special handling for mcp-orchestrator - use configured provider
    if model_name == "mcp-orchestrator":
        try:
            from .config import LLM_PROVIDER, DEFAULT_MODELS
        except ImportError:
            from config import LLM_PROVIDER, DEFAULT_MODELS
        
        print(f"DEBUG: LLM_PROVIDER = {LLM_PROVIDER}")
        print(f"DEBUG: DEFAULT_MODELS = {DEFAULT_MODELS}")
            
        default_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
        print(f"DEBUG: Using default_model = {default_model}")
        
        if LLM_PROVIDER == "huggingface":
            print("DEBUG: Creating HuggingFaceProvider")
            return HuggingFaceProvider(default_model)
        elif LLM_PROVIDER == "openai":
            print("DEBUG: Creating OpenAIProvider")
            return OpenAIProvider(default_model)
        else:
            print("DEBUG: Creating GeminiProvider")
            return GeminiProvider(default_model)
    
    # Regular model detection
    if "gemini" in model_name.lower():
        return GeminiProvider(model_name)
    elif "gpt" in model_name.lower() or "openai" in model_name.lower():
        return OpenAIProvider(model_name)
    elif "huggingface" in model_name.lower() or "/" in model_name:  # HF modely často mají formát "author/model"
        return HuggingFaceProvider(model_name)
    else:
        # Výchozí provider na základě konfigurace
        try:
            from .config import LLM_PROVIDER, DEFAULT_MODELS
        except ImportError:
            from config import LLM_PROVIDER, DEFAULT_MODELS
            
        default_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
        if LLM_PROVIDER == "huggingface":
            return HuggingFaceProvider(default_model)
        elif LLM_PROVIDER == "openai":
            return OpenAIProvider(default_model)
        else:
            return GeminiProvider(default_model)
