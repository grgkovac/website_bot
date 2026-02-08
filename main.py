import os
import json
import logfire
import httpx
import openai
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
MODERATION_ENABLED = os.getenv('MODERATION_ENABLED', 'true').lower() == 'true'

def check_openai_moderation(text: str) -> Dict[str, Any]:
    """
    Call OpenAI's Moderation API to check if text violates content policy.

    Returns dict with:
      - flagged: bool
      - categories: dict of flagged categories
      - category_scores: dict of scores per category
      - error: optional error message
    """
    if not MODERATION_ENABLED:
        return {'flagged': False, 'categories': {}, 'category_scores': {}}

    try:
        from openai import OpenAI
        client = OpenAI()
        response = client.moderations.create(input=text, timeout=10.0)
        if response and response.results:
            result = response.results[0]

            if result.flagged:
                flagged_cats = get_flagged_categories(result.categories)
                msg = {
                    "type": "text",
                    "content": f"I'm sorry, I cannot reply to that. (Content flagged for: {', '.join(flagged_cats)})"
                }

            return {
                'flagged': result.flagged,
                'categories': dict(result.categories),
                'category_scores': dict(result.category_scores),
                'msg': msg if result.flagged else None
            }

        return {'flagged': False, 'categories': {}, 'category_scores': {}, 'msg': None}

    except Exception as e:
        logfire.error(f"Moderation API error: {str(e)}")
        return {'flagged': False, 'categories': {}, 'category_scores': {}, 'error': str(e)}


def get_flagged_categories(categories: openai.types.moderation.Categories) -> List[str]:
    """Extract list of flagged category names from moderation result."""
    return [cat for cat, flagged in categories if flagged]


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
    if MODERATION_ENABLED:
        input_moderation = check_openai_moderation(request.message)

        if input_moderation.get('flagged'):
            async def blocked_response():
                yield f"data: {json.dumps(input_moderation['msg'])}\n\n"
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
                    if MODERATION_ENABLED:
                        accumulated_text = text

                        # Periodically check accumulated output (every ~500 chars to balance performance)
                        if len(accumulated_text) % 500 < 50:  # Check roughly every 500 chars
                            output_moderation = check_openai_moderation(accumulated_text)

                            if output_moderation.get('flagged'):
                                yield f"data: {json.dumps(output_moderation['msg'])}\n\n"
                                return

                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

                # Final moderation check on complete output
                if MODERATION_ENABLED and accumulated_text:
                    final_moderation = check_openai_moderation(accumulated_text)

                    if final_moderation.get('flagged'):
                        yield f"data: {json.dumps(output_moderation['msg'])}\n\n"
                        return

        except Exception as e:
            logfire.error(f"Chat endpoint error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    # 8080 is the default port for Google Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)