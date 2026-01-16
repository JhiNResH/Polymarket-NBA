"""
Configuration management using Pydantic Settings
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration"""
    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Google Gemini
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = "gemini-3-pro-preview"  # Gemini 3 Pro
    
    # The Odds API (optional)
    odds_api_key: Optional[str] = os.getenv("ODDS_API_KEY")
    
    # Scanner settings
    scan_interval_minutes: int = 30
    ev_threshold: float = 0.05  # 5%
    
    # URLs
    rotowire_url: str = "https://www.rotowire.com/basketball/nba-lineups.php"
    polymarket_api: str = "https://gamma-api.polymarket.com"
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
    
    @property
    def gemini_configured(self) -> bool:
        return bool(self.google_api_key)


# Global config instance
config = Config()
