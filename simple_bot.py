#!/usr/bin/env python3
"""
Simple Diagnostic Bot - Clean, working implementation
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleDiagnosticBot:
    def __init__(self):
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def diagnose(self, problem_description: str, command_output: str = None) -> dict:
        """Diagnose a problem and suggest next steps"""
        
        # Build the prompt
        prompt = f"""You are a system administrator helping diagnose technical issues.

Problem: {problem_description}"""
        
        if command_output:
            prompt += f"\n\nCommand output:\n{command_output}"
        
        prompt += """

Please provide:
1. A brief explanation of what might be wrong
2. A specific command to run for diagnosis (if needed)
3. Next steps

Keep your response concise and practical."""
        
        try:
            response = self.model.generate_content(prompt)
            return {
                "success": True,
                "response": response.text,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "response": None,
                "error": str(e)
            }

def main():
    """Test the simple bot"""
    print("🤖 Simple Diagnostic Bot")
    print("=" * 40)
    
    try:
        bot = SimpleDiagnosticBot()
        print("✅ Bot initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Test cases
    test_cases = [
        "I can't connect to my web server on port 8080. Getting connection refused error.",
        "My disk is full and I can't save files",
        "The system is running very slow"
    ]
    
    for i, problem in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {problem}")
        print("-" * 30)
        
        result = bot.diagnose(problem)
        
        if result["success"]:
            print("✅ Response:")
            print(result["response"])
        else:
            print(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    main()