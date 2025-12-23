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


# Deploy with Google Cloud Run

Google cloud

Project setup:
```commandline
gcloud auth login
gcloud config set project <your-project-id>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
```

Store Gemini API Key
```
echo -n "YOUR_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
```

Store OpenAI API Key
```
echo -n "YOUR_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
```

Store Logfire Token
```
echo -n "YOUR_LOGFIRE_TOKEN" | gcloud secrets create LOGFIRE_TOKEN --data-file=-
```

Grant Permission: Allow the Cloud Run Service Account to read these secrets:
```commandline
gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
    --member="<your-service-account>" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
    --member="<your-service-account>" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding LOGFIRE_TOKEN \
    --member="<your-service-account>" \
    --role="roles/secretmanager.secretAccessor"
```

Deploy to Cloud Run:
```
gcloud run deploy websitebotapi \
  --source . \
  --project <your-project-id> \
  --region <your-region> \
  --allow-unauthenticated \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,LOGFIRE_TOKEN=LOGFIRE_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest"
```

You can now access the deployed service.
To test change the `url` in the `dummy_client.py` to the Cloud Run service URL and run:
```python dummy_client.py```