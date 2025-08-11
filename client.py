#!/usr/bin/env python3
"""
Interactive diagnostic bot client - simulates real user interaction
"""
import requests
import subprocess
import json
import sys
from typing import Optional

class DiagnosticClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> dict:
        """Check API health"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status": "unreachable"}
    
    def diagnose(self, problem: str, command_output: Optional[str] = None, session_id: Optional[str] = None) -> dict:
        """Send diagnostic request"""
        payload = {"problem": problem}
        if command_output:
            payload["command_output"] = command_output
        if session_id:
            payload["session_id"] = session_id
        
        try:
            response = self.session.post(
                f"{self.base_url}/diagnose",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}

def run_command(command: str) -> dict:
    """Execute a shell command and return the result"""
    try:
        print(f"🔧 Running: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            print(f"✅ Command executed successfully")
            if output:
                print(f"📤 Output:\n{output}")
            return {"success": True, "output": output, "error": error}
        else:
            print(f"❌ Command failed (exit code: {result.returncode})")
            if error:
                print(f"📤 Error:\n{error}")
            return {"success": False, "output": output, "error": error}
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out after 30 seconds")
        return {"success": False, "output": "", "error": "Command timed out"}
    except Exception as e:
        print(f"❌ Failed to execute command: {e}")
        return {"success": False, "output": "", "error": str(e)}

def main():
    """Main interactive diagnostic session"""
    print("🤖 Interactive Diagnostic Bot Client")
    print("=" * 50)
    print("Describe your technical issue and I'll help diagnose it!")
    print("Commands will be executed automatically when suggested.")
    print("Type 'quit' to exit.\n")
    
    # Initialize client
    client = DiagnosticClient()
    
    # Quick health check
    health = client.health_check()
    if health.get("status") != "healthy":
        print("❌ API is not available. Make sure the server is running:")
        print("   python run.py")
        sys.exit(1)
    
    print("✅ Connected to diagnostic bot\n")
    
    # Main interaction loop
    current_problem = None
    session_id = None
    command_output = None
    
    while True:
        try:
            if not current_problem:
                problem = input("🔍 What technical issue are you experiencing? ").strip()
                
                if problem.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not problem:
                    continue
                
                current_problem = problem
                session_id = None  # Start new session
                command_output = None
            
            print("\n� Analy:zing...")
            
            # Debug: Show what we're sending
            if command_output:
                print(f"📋 Sending command output: {len(command_output)} characters")
            
            # Get diagnosis from API
            result = client.diagnose(current_problem, command_output, session_id)
            
            if 'error' in result:
                print(f"❌ API Error: {result['error']}")
                current_problem = None
                session_id = None
                continue
            
            # Update session ID
            session_id = result.get('session_id')
            
            # Display the diagnosis
            print(f"\n💬 {result.get('message', 'No response available')}")
            
            # Show session info
            if session_id:
                history_count = len(result.get('history', []))
                print(f"📋 Session: {session_id} | Steps: {history_count}")
            
            # Handle next steps
            if result.get('next_step') == 'command' or result.get('command'):
                command = result['command']
                print(f"\n🔧 Suggested command: {command}")
                
                # Ask user if they want to run the command
                choice = input("\nRun this command? (y/n/quit): ").strip().lower()
                
                if choice in ['quit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif choice in ['y', 'yes']:
                    # Execute the command
                    cmd_result = run_command(command)
                    print(f"🔧 Command result: {cmd_result}")

                    # trim the output to 1000 characters
                    cmd_result['output'] = cmd_result['output'][:1000]

                    # Prepare output for next API call
                    if cmd_result['success']:
                        command_output = cmd_result['output']
                        if cmd_result['error']:
                            command_output += f"\nStderr: {cmd_result['error']}"
                    else:
                        command_output = f"Command failed: {cmd_result['error']}"
                        if cmd_result['output']:
                            command_output += f"\nOutput: {cmd_result['output']}"
                    
                    print(f"\n📤 Sending command output to bot ({len(command_output)} characters)")
                    # Continue with the same problem and session
                    continue
                else:
                    print("Command skipped. You can run it manually if needed.")
                    current_problem = None
                    session_id = None
            else:
                # No command to run, diagnosis is complete
                print("\n✅ Diagnosis complete!")
                current_problem = None
                session_id = None
            
            print("\n" + "-" * 50)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            current_problem = None
            session_id = None

if __name__ == "__main__":
    main()