import os
import traceback
import logfire
from fastapi import FastAPI, HTTPException
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


class ChatResponse(BaseModel):
    reply: str
    new_history: List[ModelMessage]


# 5. The Chat Endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Run the agent with history
        result = await agent.run(
            request.message,
            message_history=request.history
        )
        # breakpoint()

        # Return the response + the updated history (so the frontend can send it back next time)
        return ChatResponse(
            reply=result.output,
            new_history=result.all_messages()
        )
    except Exception as e:
        logfire.error(f"Agent error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # 8080 is the default port for Google Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)