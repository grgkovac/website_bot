import os
import json
import traceback
import logfire
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from pydantic_ai.messages import ModelMessage

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
    history: Optional[List[ModelMessage]] = []


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    async def stream_generator():
        try:
            # Run the agent with history
            async with agent.run_stream(request.message, message_history=request.history) as result:
                async for text in result.stream_text(debounce_by=0.01):
                    yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

            final_history = result.all_messages()

            history_json = [m.model_dump() for m in final_history]
            yield f"data: {json.dumps({'type': 'history', 'content': history_json})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    # 8080 is the default port for Google Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)