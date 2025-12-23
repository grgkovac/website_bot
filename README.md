# website_bot

A chatbot to connect to my personal website and explain my research.

## Features

- Fetches and provides access to research papers and leaderboard data.
- Supports interactive chat functionality with history.
- Built using FastAPI for the backend and integrates with Pydantic AI.

# Installation

Clone the repository:
```bash
git clone https://github.com/grgkovac/website_bot.git
cd website_bot
```
   
Create conda env:
```commandline
conda create --name website_bot_env python=3.10
conda activate website_bot_env
```

Install dependencies:  
```pip install -r requirements.txt```

Setup logfire:
```commandline
logfire auth # follow the instructions to authenticate
logfire projects new # create a new project and note the project ID
# or
logfire projects use <project_id> # use an existing project
```

Run the application:  
```python main.py```

Test the chatbot using the dummy client:  
```python dummy_client.py```

# API Endpoints
POST `/chat`

- Description: Handles chat requests and returns the agent's response.
- Request Body:
```
{
  "message": "Your message here",
  "history": []
}
```
Response:
```
{
  "reply": "Agent's reply",
  "new_history": []
}
```
