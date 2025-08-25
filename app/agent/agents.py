from google import genai
from pydantic import BaseModel
from typing import Type
from app.config.config import GEMINI_API_KEY  # Load API key from env

# Lazy client (initialized on first use) to avoid startup failures when env is missing
_client: genai.Client | None = None

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

def custom_agent(
    system_prompt: str,
    user_query: str,
    response_model: Type[BaseModel],
    model_name: str = "gemini-2.0-flash"
):
    """
    Sends a system prompt and user query to Gemini, parses the response with a Pydantic model.

    Args:
        system_prompt (str): The system message prompt.
        user_query (str): The user message/query.
        response_model (Type[BaseModel]): Pydantic model class to parse the output.
        model_name (str): Gemini model to use. Defaults to 'gemini-1.5-pro'.

    Returns:
        An instance of the response_model parsed from the output.
    """

    full_prompt = f"{system_prompt}\n\n user query  : {user_query}"

    # Generate content
    client = _get_client()
    response = client.models.generate_content(
        model=model_name, contents=full_prompt,config={
        "response_mime_type": "application/json",
        "response_schema": response_model,
    })

    # Parse response
    return response.parsed  # This will be an instance of the Pydantic model