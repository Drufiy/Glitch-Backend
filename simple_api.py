#!/usr/bin/env python3
"""
Simple FastAPI server for the diagnostic bot
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Simple Diagnostic Bot", version="1.0.0")

# Configure Google AI
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

class DiagnoseRequest(BaseModel):
    problem: str
    command_output: Optional[str] = None

class DiagnoseResponse(BaseModel):
    message: str
    command: Optional[str] = None
    next_step: str  # "command" or "message"

@app.get("/")
def root():
    return {"message": "Simple Diagnostic Bot API", "status": "running"}

@app.get("/health")
def health():
    try:
        # Test Google AI
        test_response = model.generate_content("Hello")
        return {"status": "healthy", "google_ai": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest):
    """Diagnose a technical problem"""
    
    # Build prompt
    prompt = f"""You are a system administrator helping diagnose technical issues.

Problem: {request.problem}"""
    
    if request.command_output:
        prompt += f"\n\nCommand output:\n{request.command_output}"
    
    prompt += """

IMPORTANT: This is a macOS system. Use macOS-compatible commands:
- Use 'top -l 1' instead of 'top -bn1' 
- Use 'df -h' for disk usage
- Use 'ps aux' for processes
- Use 'netstat -an' for network connections
- Use 'lsof' for open files

You must respond with ONLY a JSON object in this exact format:
{
  "message": "your explanation here",
  "command": "command to run or null",
  "next_step": "command or message"
}

Rules:
- If you need the user to run a command, set "command" to the exact command and "next_step" to "command"
- If you're providing final advice or need more info, set "command" to null and "next_step" to "message"
- Keep message concise and practical
- Only suggest one command at a time
- Use macOS-compatible command syntax"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up the response if it has markdown formatting
        if response_text.startswith('```json'):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith('```'):
            response_text = response_text[3:-3].strip()
        
        # Parse JSON response
        import json
        try:
            parsed = json.loads(response_text)
            
            # Ensure command is either a string or None
            command = parsed.get("command")
            if command == "null" or command == "":
                command = None
            
            return DiagnoseResponse(
                message=parsed.get("message", "I need more information to help you."),
                command=command,
                next_step=parsed.get("next_step", "message")
            )
        except json.JSONDecodeError as e:
            # Log the problematic response for debugging
            print(f"JSON Parse Error: {e}")
            print(f"Raw response: {response_text}")
            
            # Fallback if JSON parsing fails
            return DiagnoseResponse(
                message=f"I understand you're having an issue. {response_text[:200]}",
                command=None,
                next_step="message"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)