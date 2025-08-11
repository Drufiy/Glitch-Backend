import google.generativeai as genai
from app.config.setting import settings
from app.models.model import DiagnosisOutput, HistoryEntry
from typing import List, Optional
from datetime import datetime
import uuid
import json

# Configure Google AI
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Try structured output first, fallback to regular model
try:
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=DiagnosisOutput.model_json_schema()
        )
    )
    STRUCTURED_OUTPUT = True
    print("✅ Using structured output mode")
except Exception as e:
    print(f"⚠️  Structured output not available: {e}")
    print("📝 Falling back to JSON parsing mode")
    model = genai.GenerativeModel('gemini-1.5-flash')
    STRUCTURED_OUTPUT = False

# In-memory session storage (use Redis/database in production)
sessions = {}

def truncate_output(text: str, max_length: int = 2000) -> str:
    """Truncate command output if too long"""
    if not text or len(text) <= max_length:
        return text
    
    # Keep first and last parts with truncation notice
    keep_length = max_length // 2 - 50
    truncated = (
        text[:keep_length] + 
        f"\n\n... [TRUNCATED: {len(text) - max_length} characters removed] ...\n\n" + 
        text[-keep_length:]
    )
    return truncated

def get_or_create_session(session_id: Optional[str] = None) -> tuple[str, List[HistoryEntry]]:
    """Get existing session or create new one"""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    
    # Create new session
    new_session_id = str(uuid.uuid4())[:8]
    sessions[new_session_id] = []
    return new_session_id, sessions[new_session_id]

def add_to_history(session_id: str, message: str, command: Optional[str] = None, command_output: Optional[str] = None):
    """Add entry to session history"""
    if session_id not in sessions:
        sessions[session_id] = []
    
    # Truncate command output if too long
    if command_output:
        command_output = truncate_output(command_output)
    
    entry = HistoryEntry(
        timestamp=datetime.now(),
        message=message,
        command=command,
        command_output=command_output
    )
    
    sessions[session_id].append(entry)
    
    # Keep only last 10 entries to prevent memory issues
    if len(sessions[session_id]) > 10:
        sessions[session_id] = sessions[session_id][-10:]

def load_prompt_template():
    """Load the prompt template from file"""
    with open('app/prompts/prompt.txt', 'r') as f:
        return f.read()

def build_prompt_with_history(problem: str, history: List[HistoryEntry], command_output: str = None):
    """Build prompt including session history"""
    template = load_prompt_template()
    
    # Build history context
    history_section = ""
    if history:
        history_section = "\n\nPREVIOUS CONVERSATION HISTORY:"
        for i, entry in enumerate(history[-5:], 1):  # Last 5 entries
            history_section += f"\n\nStep {i} ({entry.timestamp.strftime('%H:%M:%S')}):"
            history_section += f"\nBot: {entry.message}"
            if entry.command:
                history_section += f"\nSuggested Command: {entry.command}"
            if entry.command_output:
                history_section += f"\nCommand Output: {entry.command_output}"
    
    # Current command output
    command_output_section = ""
    if command_output:
        command_output = truncate_output(command_output)
        command_output_section = f"\n\nCURRENT COMMAND OUTPUT:\n{command_output}"
    
    prompt = template.format(
        problem=problem,
        history_section=history_section,
        command_output_section=command_output_section
    )
    
    # Add JSON format instruction only if not using structured output
    if not STRUCTURED_OUTPUT:
        prompt += """

You must respond with ONLY a JSON object in this exact format:
{
  "message": "your explanation here",
  "command": "command to run or null",
  "next_step": "command or message"
}"""
    
    return prompt

def clean_response_text(response_text: str):
    """Clean up AI response text by removing markdown formatting"""
    response_text = response_text.strip()
    
    if response_text.startswith('```json'):
        response_text = response_text[7:-3].strip()
    elif response_text.startswith('```'):
        response_text = response_text[3:-3].strip()
    
    return response_text

def parse_ai_response(response_text: str):
    """Parse AI response and return structured data"""
    try:
        parsed = json.loads(response_text)
        
        # Ensure command is either a string or None
        command = parsed.get("command")
        if command == "null" or command == "" or command is None:
            command = None
        
        # Debug logging
        print(f"🔍 AI Response Debug:")
        print(f"   Message: {parsed.get('message', 'No message')[:100]}...")
        print(f"   Command: {command}")
        print(f"   Next Step: {parsed.get('next_step', 'No next_step')}")
        
        return {
            "message": parsed.get("message", "I need more information to help you."),
            "command": command,
            "next_step": parsed.get("next_step", "message")
        }
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw response: {response_text}")
        
        # Fallback response
        return {
            "message": f"I understand you're having an issue. {response_text[:200]}",
            "command": None,
            "next_step": "message"
        }

def generate_diagnosis(problem: str, command_output: str = None, session_id: Optional[str] = None):
    """Generate diagnosis using AI model with session history"""
    # Get or create session
    session_id, history = get_or_create_session(session_id)
    
    # Build prompt with history
    prompt = build_prompt_with_history(problem, history, command_output)
    
    try:
        response = model.generate_content(prompt)
        
        if STRUCTURED_OUTPUT:
            # Parse structured JSON response directly
            diagnosis = DiagnosisOutput.model_validate_json(response.text)
            diagnosis_data = {
                "message": diagnosis.message,
                "command": diagnosis.command,
                "next_step": diagnosis.next_step
            }
            print(f"🔍 Structured Response Debug:")
            print(f"   Message: {diagnosis.message[:100]}...")
            print(f"   Command: {diagnosis.command}")
            print(f"   Next Step: {diagnosis.next_step}")
        else:
            # Use traditional JSON parsing
            response_text = clean_response_text(response.text)
            print(f"🔍 Raw AI Response: {response_text}")
            diagnosis_data = parse_ai_response(response_text)
        
        # Add to history
        add_to_history(
            session_id, 
            diagnosis_data["message"], 
            diagnosis_data["command"], 
            command_output
        )
        
        return {
            "message": diagnosis_data["message"],
            "command": diagnosis_data["command"],
            "next_step": diagnosis_data["next_step"],
            "session_id": session_id,
            "history": sessions[session_id]
        }
        
    except Exception as e:
        print(f"Error generating diagnosis: {e}")
        
        # Fallback response
        fallback_message = "I'm having trouble processing your request. Please try again with more details about the issue."
        add_to_history(session_id, fallback_message, None, command_output)
        
        return {
            "message": fallback_message,
            "command": None,
            "next_step": "message",
            "session_id": session_id,
            "history": sessions[session_id]
        }