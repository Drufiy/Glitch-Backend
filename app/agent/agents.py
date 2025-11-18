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

    # Add JSON schema instruction to prompt for structured output
    import json
    schema_dict = response_model.model_json_schema()
    schema_json = json.dumps(schema_dict, indent=2)
    
    # Build prompt with clear JSON format instructions
    full_prompt = f"""{system_prompt}

**CRITICAL: Respond with ONLY valid JSON matching this schema:**
{schema_json}

**Response format rules:**
- "message": Explain what you're doing (required)
- "command": PowerShell command to execute. If you provide a command, set "next_step" to "command". If no command needed, use empty string and set "next_step" to "message"
- "next_step": Use "command" when you provided a command to execute, "message" when just responding without executing

**Examples:**
- User says "open settings" → {{"message": "Opening Windows Settings...", "command": "Start-Process ms-settings:", "next_step": "command"}}
- User asks a question → {{"message": "Answer here", "command": "", "next_step": "message"}}

**Your response (ONLY JSON, no markdown):**
User query: {user_query}"""

    # Generate content
    client = _get_client()
    max_retries = 2
    models_to_try = [model_name, "gemini-2.5-flash", "gemini-2.0-flash"]
    
    for attempt, current_model in enumerate(models_to_try[:max_retries + 1]):
        try:
            print(f"[Attempt {attempt + 1}] Using model {current_model}")
            # Use simple text generation first, then parse JSON
            response = client.models.generate_content(
                model=current_model,
                contents=full_prompt
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            print(f"[Raw response] First 200 chars: {response_text[:200]}")
            
            # Clean up response text - remove markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()
            
            # Remove any leading/trailing whitespace or newlines
            response_text = response_text.strip()
            
            # Try to find JSON object in the text
            if response_text.startswith("{"):
                json_end = response_text.rfind("}") + 1
                if json_end > 0:
                    response_text = response_text[:json_end]
            
            # Parse JSON
            try:
                parsed_data = json.loads(response_text)
                print(f"[SUCCESS] Parsed JSON: {parsed_data}")
                # Validate and create response model instance
                return response_model(**parsed_data)
            except json.JSONDecodeError as json_error:
                print(f"[WARNING] JSON parse error: {json_error}")
                print(f"   Attempted to parse: {response_text[:500]}")
                if attempt < max_retries:
                    continue
                # Last resort: try to extract just the JSON part
                import re
                json_match = re.search(r'\{[^{}]*"message"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_data = json.loads(json_match.group())
                        return response_model(**parsed_data)
                    except:
                        pass
                raise ValueError(f"Failed to parse JSON from response: {response_text[:500]}")
                
        except Exception as e:
            print(f"Error with model {current_model}: {type(e).__name__}: {e}")
            if attempt < max_retries:
                print(f" Retrying with next model...")
                continue
            else:
                # Last attempt failed - return a fallback response
                print(f"All attempts failed. Returning fallback response.")
                return response_model(
                    message=f"I encountered an error processing your request. Please try again. Error: {str(e)[:100]}",
                    command="",
                    next_step="message"
                )
    
    # Should not reach here, but just in case
    return response_model(
        message="Unable to process request. Please try again.",
        command="",
        next_step="message"
    )
