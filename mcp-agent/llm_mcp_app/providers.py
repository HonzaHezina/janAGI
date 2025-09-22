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
                        GEMINI_API_KEY, HUGGINGFACE_API_KEY, OPENAI_API_KEY,
                        MISTRAL_API_BASE, MISTRAL_API_KEY)
except ImportError:
    from models import ChatCompletionRequest, Message
    from config import (logger, GEMINI_API_BASE, HUGGINGFACE_API_BASE, OPENAI_API_BASE,
                       GEMINI_API_KEY, HUGGINGFACE_API_KEY, OPENAI_API_KEY,
                       MISTRAL_API_BASE, MISTRAL_API_KEY)


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


class MistralProvider(LLMProvider):
    """
    Production-ready Mistral provider for 'codestral' family:
    - Uses configured MISTRAL_API_KEY / MISTRAL_API_BASE from config.py
    - Retries on transient errors with exponential backoff
    - Robust streaming parsing and normalized OpenAI-like chunks
    - Clear error handling for 4xx vs 5xx
    """
    def __init__(self, model_name: str):
        super().__init__(model_name)
        # Prefer explicit config values, fall back to env
        self.api_key = MISTRAL_API_KEY or os.getenv("MISTRAL_API_KEY")
        self.api_base = MISTRAL_API_BASE or os.getenv("MISTRAL_API_BASE", "https://api.mistral.ai")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        # Retry settings
        self._max_retries = 3
        self._backoff_factor = 0.5  # seconds

    def _format_messages(self, messages: List[Message]) -> str:
        # Convert messages to a single prompt string expected by Mistral
        conversation = ""
        for msg in messages:
            role = msg.role.capitalize() if hasattr(msg, "role") else "User"
            conversation += f"{role}: {msg.content}\n"
        conversation += "Assistant: "
        return conversation

    async def _request_with_retries(self, method: str, url: str, headers: Dict[str, str], json_data: Dict[str, Any], timeout: float = 60.0):
        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(method, url, headers=headers, json=json_data, timeout=timeout)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                text = e.response.text
                # Client errors - do not retry
                if 400 <= status < 500:
                    logger.error(f"Mistral API client error ({status}): {text}")
                    raise HTTPException(status_code=status, detail=f"Mistral API client error: {text}")
                # Server errors - retry up to limit
                attempt += 1
                logger.warning(f"Mistral API server error ({status}) on attempt {attempt}: {text}")
                if attempt >= self._max_retries:
                    logger.error(f"Mistral API failed after {attempt} attempts: {text}")
                    raise HTTPException(status_code=status, detail=f"Mistral API server error after retries: {text}")
                await self._sleep_backoff(attempt)
            except (httpx.RequestError, Exception) as e:
                attempt += 1
                logger.warning(f"Mistral request error on attempt {attempt}: {e}")
                if attempt >= self._max_retries:
                    logger.error(f"Mistral API request failed after {attempt} attempts: {e}")
                    raise HTTPException(status_code=500, detail=f"Mistral API request failed: {e}")
                await self._sleep_backoff(attempt)

    async def _sleep_backoff(self, attempt: int):
        await __import__("asyncio").sleep(self._backoff_factor * (2 ** (attempt - 1)))

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        prompt = self._format_messages(request.messages)
        payload = {
            "model": self.model_name,
            "input": prompt,
            "max_tokens": request.max_tokens or 512,
            "temperature": request.temperature or 0.7
        }
        url = f"{self.api_base.rstrip('/')}/v1/generate"
        resp = await self._request_with_retries("POST", url, headers, payload, timeout=60.0)
        try:
            return resp.json()
        except Exception:
            text = await resp.text()
            logger.error(f"Failed to decode Mistral response JSON: {text}")
            raise HTTPException(status_code=500, detail="Invalid JSON from Mistral API")

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """
        Stream generate: handles line-delimited / SSE-like streaming responses and
        yields OpenAI-like chunks: 'data: {...}\\n\\n' and final 'data: [DONE]'.
        """
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "input": self._format_messages(request.messages),
            "max_tokens": request.max_tokens or 512,
            "temperature": request.temperature or 0.7,
            "stream": True
        }
        url = f"{self.api_base.rstrip('/')}/v1/generate"
        attempt = 0
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream("POST", url, headers=headers, json=payload, timeout=120.0) as response:
                        response.raise_for_status()
                        buffer = ""
                        async for raw_line in response.aiter_lines():
                            if raw_line is None:
                                continue
                            line = raw_line.strip()
                            if not line:
                                continue
                            # Mistral streaming may send json objects per line or SSE-style "data: {...}"
                            if line.startswith("data: "):
                                line = line[len("data: "):]
                            try:
                                obj = json.loads(line)
                            except Exception:
                                # yield raw text as chunk
                                obj = {"text": line}
                            # Try to extract text from known shapes
                            text_chunk = ""
                            if isinstance(obj, dict):
                                # Common newer Mistral shape: {"outputs":[{"content":[{"type":"output_text","text":"..."}]}]}
                                outputs = obj.get("outputs") or obj.get("output") or obj.get("generations")
                                if outputs and isinstance(outputs, list):
                                    first = outputs[0]
                                    content = first.get("content") if isinstance(first, dict) else None
                                    if isinstance(content, list):
                                        parts = []
                                        for block in content:
                                            if isinstance(block, dict):
                                                parts.append(block.get("text") or block.get("content") or "")
                                            else:
                                                parts.append(str(block))
                                        text_chunk = "".join(parts)
                                    elif isinstance(first, dict) and "text" in first:
                                        text_chunk = first.get("text", "")
                                elif "text" in obj:
                                    text_chunk = obj.get("text", "")
                                elif "generated_text" in obj:
                                    text_chunk = obj.get("generated_text", "")
                                else:
                                    # fallback to stringifying object
                                    text_chunk = str(obj)
                            else:
                                text_chunk = str(obj)
                            if text_chunk:
                                chunk = {
                                    "id": f"chatcmpl-mistral-{os.urandom(6).hex()}",
                                    "object": "chat.completion.chunk",
                                    "created": int(time.time()),
                                    "model": self.model_name,
                                    "choices": [{"index": 0, "delta": {"content": text_chunk}, "finish_reason": None}]
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                        # final chunk
                        final_chunk = {
                            "id": f"chatcmpl-mistral-{os.urandom(6).hex()}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": self.model_name,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                text = e.response.text
                # client errors - surface and finish stream
                if 400 <= status < 500:
                    logger.error(f"Mistral streaming client error ({status}): {text}")
                    error_message = {"error": {"message": f"Mistral API error: {text}", "type": "api_error", "code": status}}
                    yield f"data: {json.dumps(error_message)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                attempt += 1
                logger.warning(f"Mistral streaming server error ({status}) attempt {attempt}: {text}")
                if attempt >= self._max_retries:
                    error_message = {"error": {"message": f"Mistral API streaming error after retries: {text}", "type": "api_error", "code": status}}
                    yield f"data: {json.dumps(error_message)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                await self._sleep_backoff(attempt)
            except (httpx.RequestError, Exception) as e:
                attempt += 1
                logger.warning(f"Mistral streaming request error on attempt {attempt}: {e}")
                if attempt >= self._max_retries:
                    error_message = {"error": {"message": f"Mistral streaming request failed: {e}", "type": "server_error"}}
                    yield f"data: {json.dumps(error_message)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                await self._sleep_backoff(attempt)

    def _extract_content(self, response: Dict[str, Any]) -> str:
        """
        Robust extraction for several potential Mistral response shapes.
        """
        try:
            if not response:
                return ""
            # Newer shape: {"outputs":[{"content":[{"type":"output_text","text":"..."}]}]}
            if isinstance(response, dict):
                outputs = response.get("outputs") or response.get("output") or response.get("generations")
                if outputs and isinstance(outputs, list):
                    first = outputs[0]
                    content = first.get("content") if isinstance(first, dict) else None
                    if isinstance(content, list):
                        texts = []
                        for block in content:
                            if isinstance(block, dict):
                                texts.append(block.get("text") or block.get("content") or "")
                            else:
                                texts.append(str(block))
                        return "".join(texts)
                    # fallback if first has text key
                    if isinstance(first, dict) and "text" in first:
                        return first.get("text", "")
                # legacy keys
                if "generated_text" in response:
                    return response.get("generated_text", "")
                if "text" in response:
                    return response.get("text", "")
                # attempt to stringify useful keys
                for key in ("output", "outputs", "generations"):
                    if key in response:
                        return str(response[key])
            return str(response)
        except Exception as e:
            logger.error(f"MistralProvider _extract_content error: {e}")
            return ""

def get_provider(model_name: str = None, provider_override: str = None) -> LLMProvider:
    """Factory to get the appropriate LLM provider.

    Accepts an optional provider_override (e.g. "openai", "huggingface", "gemini", "mistral").
    If provider_override is provided it will be used to select the provider implementation;
    otherwise provider is detected heuristically from model_name. Falls back to DummyProvider
    on instantiation errors.
    """
    # Local helper: safe instantiation with fallback
    def _safe_instantiate(provider_cls, *args, **kwargs):
        try:
            return provider_cls(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to instantiate {provider_cls.__name__}: {e}. Using DummyProvider fallback.")
            return DummyProvider(args[0] if args else "unknown")

    # Normalize inputs
    pname = provider_override.lower() if provider_override else None
    mname = model_name or ""

    # If an explicit provider override is requested, prefer it
    if pname:
        try:
            from .config import DEFAULT_MODELS
        except ImportError:
            from config import DEFAULT_MODELS

        default_model = mname or DEFAULT_MODELS.get(pname, DEFAULT_MODELS.get("openai", mname or ""))
        if pname == "huggingface":
            return _safe_instantiate(HuggingFaceProvider, default_model)
        elif pname == "openai":
            return _safe_instantiate(OpenAIProvider, default_model)
        elif pname == "mistral":
            return _safe_instantiate(MistralProvider, default_model or mname or "codestral")
        else:
            # Default to Gemini for unknown override
            return _safe_instantiate(GeminiProvider, default_model or mname or "gemini-1.5-flash")

    # Special handling for mcp-orchestrator - use configured provider
    if mname == "mcp-orchestrator":
        try:
            from .config import LLM_PROVIDER, DEFAULT_MODELS
        except ImportError:
            from config import LLM_PROVIDER, DEFAULT_MODELS

        default_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
        logger.info(f"Using orchestrator default model = {default_model} for provider {LLM_PROVIDER}")

        if LLM_PROVIDER == "huggingface":
            return _safe_instantiate(HuggingFaceProvider, default_model)
        elif LLM_PROVIDER == "openai":
            return _safe_instantiate(OpenAIProvider, default_model)
        else:
            return _safe_instantiate(GeminiProvider, default_model)

    # Regular model detection (heuristic)
    try:
        lname = mname.lower()
    except Exception:
        lname = ""

    # Detect Mistral / codestral model name explicitly
    if "codestral" in lname or "mistral" in lname:
        return _safe_instantiate(MistralProvider, mname)

    if "gemini" in lname:
        return _safe_instantiate(GeminiProvider, mname)
    elif "gpt" in lname or "openai" in lname:
        return _safe_instantiate(OpenAIProvider, mname)
    elif "huggingface" in lname or "/" in mname:  # HF models often have "author/model"
        return _safe_instantiate(HuggingFaceProvider, mname)
    else:
        # Default provider based on configuration
        try:
            from .config import LLM_PROVIDER, DEFAULT_MODELS
        except ImportError:
            from config import LLM_PROVIDER, DEFAULT_MODELS

        default_model = DEFAULT_MODELS.get(LLM_PROVIDER, "gemini-1.5-flash")
        if LLM_PROVIDER == "huggingface":
            return _safe_instantiate(HuggingFaceProvider, default_model)
        elif LLM_PROVIDER == "openai":
            return _safe_instantiate(OpenAIProvider, default_model)
        else:
            return _safe_instantiate(GeminiProvider, default_model)


# --- DummyProvider for safe fallback when API keys are missing or provider init fails ---
class DummyProvider(LLMProvider):
    def __init__(self, model_name: str):
        super().__init__(model_name)

    async def generate(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        prompt_summary = ""
        try:
            prompt_summary = " | ".join(m.content for m in request.messages[-3:])
        except Exception:
            prompt_summary = request.messages[-1].content if request.messages else ""
        text = (
            f"[DUMMY PROVIDER] Running in offline/fallback mode for model '{self.model_name}'. "
            f"Prompt summary: {prompt_summary}"
        )
        return {"generated_text": text, "dummy": True}

    async def stream_generate(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        # Simulate streaming by yielding the generated text in chunks
        response = await self.generate(request)
        content = self._extract_content(response)
        for i in range(0, len(content), 120):
            chunk = {"id": f"chatcmpl-dummy-{os.urandom(6).hex()}", "object": "chat.completion.chunk",
                     "created": int(time.time()), "model": self.model_name,
                     "choices": [{"index": 0, "delta": {"content": content[i:i+120]}, "finish_reason": None}]}
            yield f"data: {json.dumps(chunk)}\n\n"
        final_chunk = {"id": f"chatcmpl-dummy-{os.urandom(6).hex()}", "object": "chat.completion.chunk",
                       "created": int(time.time()), "model": self.model_name,
                       "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def _extract_content(self, response: Dict[str, Any]) -> str:
        try:
            # Support both HF-like and generic responses
            if isinstance(response, dict):
                return response.get("generated_text") or response.get("text") or str(response)
            return str(response)
        except Exception as e:
            logger.error(f"DummyProvider _extract_content error: {e}")
            return ""
