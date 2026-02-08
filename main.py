import os
import json
import logfire
import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart

# 1. Setup Logfire (Make sure you've run 'logfire auth' in your terminal)
logfire.configure()
logfire.instrument_pydantic_ai()

# 2. Import your Agent and Tools (Assuming they are in agent_logic.py)
# For this snippet, I'll assume 'agent' is your Pydantic AI agent instance.
from agent import agent

app = FastAPI(title="Grgur's Research Assistant API")

# 3. Enable CORS for your GitHub Pages site
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["https://grgkovac.github.io"],
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Moderation Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
MODERATION_ENABLED = os.getenv('MODERATION_ENABLED', 'true').lower() == 'true'
MODERATE_INPUT = os.getenv('MODERATE_INPUT', 'true').lower() == 'true'
MODERATE_OUTPUT = os.getenv('MODERATE_OUTPUT', 'true').lower() == 'true'
MODERATION_ACTION = os.getenv('MODERATION_ACTION', 'block').lower()  # block | warn | log


async def check_openai_moderation(text: str) -> Dict[str, Any]:
    """
    Call OpenAI's Moderation API to check if text violates content policy.

    Returns dict with:
      - flagged: bool
      - categories: dict of flagged categories
      - category_scores: dict of scores per category
      - error: optional error message
    """
    if not MODERATION_ENABLED or not OPENAI_API_KEY:
        return {'flagged': False, 'categories': {}, 'category_scores': {}}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                'https://api.openai.com/v1/moderations',
                headers={
                    'Authorization': f'Bearer {OPENAI_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={'input': text}
            )
            response.raise_for_status()
            data = response.json()

            if data.get('results'):
                result = data['results'][0]
                return {
                    'flagged': result.get('flagged', False),
                    'categories': result.get('categories', {}),
                    'category_scores': result.get('category_scores', {}),
                }

            return {'flagged': False, 'categories': {}, 'category_scores': {}}

    except Exception as e:
        logfire.error(f"Moderation API error: {str(e)}")
        return {'flagged': False, 'categories': {}, 'category_scores': {}, 'error': str(e)}


def get_flagged_categories(moderation_result: Dict[str, Any]) -> List[str]:
    """Extract list of flagged category names from moderation result."""
    categories = moderation_result.get('categories', {})
    return [cat for cat, flagged in categories.items() if flagged]


# 4. Request/Response Models
class ChatRequest(BaseModel):
    message: str
    # Change type to List[dict] to accept simple JSON from the browser
    history: Optional[List[dict]] = []

# Minimal helper to convert simple JS dicts to Pydantic AI objects
def format_history(history_data: List[dict]) -> List[ModelMessage]:
    formatted = []
    for msg in history_data:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'user':
            formatted.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == 'model':
            formatted.append(ModelResponse(parts=[TextPart(content=content)]))
    return formatted

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Moderate user input first
    if MODERATE_INPUT and MODERATION_ENABLED:
        input_moderation = await check_openai_moderation(request.message)

        if input_moderation.get('flagged'):
            flagged_cats = get_flagged_categories(input_moderation)
            logfire.warn(f"User input flagged for: {', '.join(flagged_cats)}")

            if MODERATION_ACTION == 'block':
                # Return polite message via streaming instead of HTTPException
                async def blocked_response():
                    msg = {"type": "text", "content": "I'm sorry, I cannot reply to that."}
                    yield f"data: {json.dumps(msg)}\n\n"
                return StreamingResponse(blocked_response(), media_type="text/event-stream")

    async def stream_generator():
        try:
            # Convert the raw dicts into the objects the agent expects
            message_history = format_history(request.history)

            # Run the agent with history
            async with agent.run_stream(request.message, message_history=message_history) as result:
                accumulated_text = ""

                async for text in result.stream_text(debounce_by=0.01):
                    # Accumulate text for moderation check
                    if MODERATE_OUTPUT and MODERATION_ENABLED:
                        accumulated_text = text

                        # Periodically check accumulated output (every ~500 chars to balance performance)
                        if len(accumulated_text) % 500 < 50:  # Check roughly every 500 chars
                            output_moderation = await check_openai_moderation(accumulated_text)

                            if output_moderation.get('flagged'):
                                flagged_cats = get_flagged_categories(output_moderation)
                                logfire.warn(f"Agent output flagged for: {', '.join(flagged_cats)}")

                                if MODERATION_ACTION == 'block':
                                    msg = {"type": "text", "content": "I'm sorry, I cannot reply to that."}
                                    yield f"data: {json.dumps(msg)}\n\n"
                                    return
                                elif MODERATION_ACTION == 'warn':
                                    warning_msg = f"Content warning: {', '.join(flagged_cats)}"
                                    msg = {"type": "warning", "content": warning_msg}
                                    yield f"data: {json.dumps(msg)}\n\n"

                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

                # Final moderation check on complete output
                if MODERATE_OUTPUT and MODERATION_ENABLED and accumulated_text:
                    final_moderation = await check_openai_moderation(accumulated_text)

                    if final_moderation.get('flagged'):
                        flagged_cats = get_flagged_categories(final_moderation)
                        logfire.warn(f"Final agent output flagged for: {', '.join(flagged_cats)}")

                        if MODERATION_ACTION == 'warn':
                            warning_msg = f"Content completed with warnings: {', '.join(flagged_cats)}"
                            msg = {"type": "warning", "content": warning_msg}
                            yield f"data: {json.dumps(msg)}\n\n"

        except Exception as e:
            logfire.error(f"Chat endpoint error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    # 8080 is the default port for Google Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)