from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Tamil Movies Scraper API"
    VERSION: str = "1.0.0"
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    class Config:
        case_sensitive = True

settings = Settings()