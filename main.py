import os
import json
import traceback
import logfire
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
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
    async def stream_generator():
        try:
            # Convert the raw dicts into the objects the agent expects
            message_history = format_history(request.history)

            # Run the agent with history
            async with agent.run_stream(request.message, message_history=message_history) as result:
                async for text in result.stream_text(debounce_by=0.01):
                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    # 8080 is the default port for Google Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)