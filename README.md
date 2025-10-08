# AI Growth Analyst Agent

This is the backend API for an AI-Powered Growth Analyst. It's a FastAPI service that lets you chat with an AI that can pull insights from Google Analytics, Google Ads, and Google Search Console.

## Getting Started

### Without Docker

1. Install dependencies using uv (recommended):
   ```bash
   pip install uv
   uv sync
   ```

   Or using pip:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your environment variables by creating a `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Fill in your credentials in `.env`:
   - Azure OpenAI credentials
   - Cosmos DB settings
   - Data service URL

4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000)

### With Docker

1. Create your `.env` file with the required credentials

2. Build and run with Docker:
   ```bash
   docker build -t ai-growth-analyst-agent .
   docker run -p 8000:8000 --env-file .env ai-growth-analyst-agent
   ```

   Access the API at [http://localhost:8000](http://localhost:8000)

## What's Inside

- **AI Agent** - LangGraph-powered agent that can query marketing platforms
- **Google Analytics** - Pull GA4 metrics and insights
- **Google Ads** - Get campaign performance data
- **Google Search Console** - Analyze search performance
- **Chat API** - REST endpoints for conversational analysis
- **Cosmos DB** - Store conversation history

## API Docs

Once running, check out the interactive API documentation:
- Swagger UI: http://localhost:8000/docs