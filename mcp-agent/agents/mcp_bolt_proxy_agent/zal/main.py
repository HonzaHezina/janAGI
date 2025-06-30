import os
import uvicorn
import httpx
import json
import time
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status, Depends, HTTPException, APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from http import HTTPStatus

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="MCP Bolt Proxy Agent",
    description="Proxy agent for integrating LLMs with the Bolt.diy application, providing an OpenAI-like API.",
    version="0.1.0",
)

api_router = APIRouter(prefix="/v1")

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models" # Default Gemini API base URL

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set.")
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# --- Pydantic Models for OpenAI-like API ---

class ChatCompletionMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionMessage
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-proxy"
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage

class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "google"

class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelObject]

# --- Helper function to translate OpenAI to Gemini format ---
def openai_to_gemini_messages(openai_messages: List[ChatCompletionMessage]) -> List[Dict[str, Any]]:
    gemini_messages = []
    for msg in openai_messages:
        # Gemini expects 'user' and 'model' roles
        role = "user" if msg.role == "user" else "model" if msg.role == "assistant" else "user" # Default to user for system/tool
        gemini_messages.append({"role": role, "parts": [{"text": msg.content}]})
    return gemini_messages

# --- API Endpoints ---
@api_router.get("/models", response_model=ModelList)
async def list_models():
    """
    Lists the models available via this proxy.
    """
    logger.info("Received request for /v1/models")
    supported_models = [
        ModelObject(id="gemini-pro"),
        ModelObject(id="gemini-pro-vision"),
        ModelObject(id="gemini-2.5-flash"),
        ModelObject(id="gemini-2.5-flash-exp-native-audio-thinking-dialog"),
        # Add other Gemini models as needed
    ]
    logger.info(f"Returning supported models: {[m.id for m in supported_models]}")
    return ModelList(data=supported_models)

@api_router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """
    Handles chat completion requests, proxies them to Gemini API, and returns an OpenAI-like response.
    """
    logger.info(f"Received chat completion request for model: {request.model}, stream: {request.stream}")
    logger.debug(f"Request details: {json.dumps(request.dict(), indent=2)}")

    if not GEMINI_API_KEY:
        logger.error("Gemini API Key not configured during request processing.")
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Gemini API Key not configured.")

    gemini_model_name = request.model
    gemini_url = f"{GEMINI_API_BASE_URL}/{gemini_model_name}:generateContent?key={GEMINI_API_KEY}"

    gemini_request_payload = {
        "contents": openai_to_gemini_messages(request.messages),
        "generationConfig": {
            "temperature": request.temperature,
            "topP": request.top_p,
            "maxOutputTokens": request.max_tokens,
            "stopSequences": request.stop,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    }

    if request.stream:
        logger.info("Handling streaming request.")
        async def generate_stream():
            async with httpx.AsyncClient() as client:
                try:
                    # For streaming, Gemini API uses a different endpoint suffix and returns newline-delimited JSON
                    stream_url = f"{gemini_url}&alt=sse" # Add alt=sse for Server-Sent Events
                    logger.info(f"Sending streaming request to Gemini API URL: {stream_url}")
                    logger.debug(f"Gemini request payload (streaming): {json.dumps(gemini_request_payload, indent=2)}")

                    async with client.stream("POST", stream_url, json=gemini_request_payload, timeout=60.0) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            chunk_str = chunk.decode('utf-8')
                            # Gemini API sends newline-delimited JSON objects
                            for line in chunk_str.splitlines():
                                if line.strip():
                                    try:
                                        gemini_chunk = json.loads(line)
                                        logger.debug(f"Received stream chunk from Gemini API: {json.dumps(gemini_chunk, indent=2)}")

                                        # Assuming the first part is text
                                        generated_text = first_candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
                                        logger.debug(f"Extracted generated_text (streaming): {generated_text}")
                                        finish_reason = first_candidate.get("finishReason", None)

                                        # Extract token usage if available in stream (usually in the last chunk)
                                        if "usageMetadata" in gemini_chunk:
                                            usage_metadata = gemini_chunk["usageMetadata"]
                                            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                                            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                                            total_tokens = usage_metadata.get("totalTokenCount", 0)

                                            # We can send usage as a separate chunk or ignore it for streaming
                                            # For simplicity, we are not sending it in each chunk, but it is available in the log
                                            logger.info(f"Stream usage: prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, total_tokens={total_tokens}")

                                    except json.JSONDecodeError:
                                        logger.warning(f"Could not decode JSON from chunk: {line}")
                                        # It can happen that a chunk is not a complete JSON, we wait for the next one
                                        pass
                                    except Exception as e:
                                        logger.error(f"Error processing stream chunk: {e}")
                                        # Continue processing other chunks even if one fails
                                        pass
                    yield "data: [DONE]\n\n".encode('utf-8') # Signal end of stream
                except httpx.RequestError as exc:
                    logger.error(f"An error occurred while requesting Gemini API (streaming): {exc}")
                    yield f"data: {json.dumps({'error': f'An error occurred while requesting Gemini API: {exc}'})}\n\n".encode('utf-8')
                except httpx.HTTPStatusError as exc:
                    logger.error(f"Gemini API returned an error (streaming): {exc.response.status_code} - {exc.response.text}")
                    yield f"data: {json.dumps({'error': f'Gemini API returned an error: {exc.response.text}'})}\n\n".encode('utf-8')
                except Exception as exc:
                    logger.error(f"An unexpected error occurred (streaming): {exc}")
                    yield f"data: {json.dumps({'error': f'An unexpected error occurred: {exc}'})}\n\n".encode('utf-8')

        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        # Non-streaming response (existing logic)
        logger.info("Handling non-streaming request.")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(gemini_url, json=gemini_request_payload, timeout=60.0)
                response.raise_for_status()
                gemini_response = response.json()
                logger.info(f"Received response from Gemini API (non-streaming): {json.dumps(gemini_response, indent=2)}")
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting Gemini API (non-streaming): {exc}")
                raise HTTPException(
                    status_code=HTTPStatus.BAD_GATEWAY,
                    detail=f"An error occurred while requesting Gemini API: {exc}"
                )
            except httpx.HTTPStatusError as exc:
                logger.error(f"Gemini API returned an error (non-streaming): {exc.response.status_code} - {exc.response.text}")
                raise HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"Gemini API returned an error: {exc.response.text}"
                )
            except Exception as exc:
                logger.error(f"An unexpected error occurred (non-streaming): {exc}")
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {exc}"
                )

        # Translate Gemini response back to OpenAI-like format
        if not gemini_response or "candidates" not in gemini_response or not gemini_response["candidates"]:
            logger.warning("No candidates found in Gemini response (non-streaming).")
            raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail="No candidates found in Gemini response.")

        first_candidate = gemini_response["candidates"][0]
        if "content" not in first_candidate or "parts" not in first_candidate["content"]:
            logger.warning("Invalid content structure in Gemini response (non-streaming).")
            raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail="Invalid content structure in Gemini response.")

        generated_text = first_candidate["content"]["parts"][0]["text"]
        logger.debug(f"Extracted generated_text (non-streaming): {generated_text}")
        finish_reason = first_candidate.get("finishReason", "stop")

        # Extract token usage if available, otherwise estimate
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if "usageMetadata" in gemini_response:
            usage_metadata = gemini_response["usageMetadata"]
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)
            logger.info(f"Token usage from Gemini API (non-streaming): prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, total_tokens={total_tokens}")
        else:
            # Fallback estimation if usageMetadata is not present
            # This is a very rough estimate and might not be accurate
            prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
            completion_tokens = len(generated_text.split())
            total_tokens = prompt_tokens + completion_tokens
            logger.warning(f"Usage metadata not found in Gemini response (non-streaming). Estimating tokens: prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, total_tokens={total_tokens}")


        openai_response = ChatCompletionResponse(
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content=generated_text),
                    finish_reason=finish_reason.lower()
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

        logger.info(f"Sending OpenAI-like response to bolt.diy (non-streaming): {json.dumps(openai_response.dict(), indent=2)}")

        return openai_response


app.include_router(api_router) # Include the router with /v1 prefix

@app.get("/")
async def root():
    return {"message": "MCP Bolt Proxy Agent is running!"}

# --- Main execution block for running the FastAPI server ---
if __name__ == "__main__":
    # The port can be configured in mcp_agent.config.yaml or as an environment variable
    # For now, hardcode to 8000 as per bolt.diy config
    port = int(os.getenv("PROXY_PORT", 8000))
    host = os.getenv("PROXY_HOST", "0.0.0.0") # Listen on all interfaces

    logger.info(f"Starting MCP Bolt Proxy Agent on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)