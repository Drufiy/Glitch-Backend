import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # API Configuration
    API_TITLE = "Simple Diagnostic Bot"
    API_VERSION = "1.0.0"
    
    # Google AI
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    
    # Server
    HOST = "0.0.0.0"
    PORT = int(os.getenv('PORT', 8080))
    
    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment")

settings = Settings()
settings.validate()