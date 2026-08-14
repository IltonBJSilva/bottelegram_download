from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_API_SERVER: Optional[str] = None
    
    ALLOWED_USER_IDS: str = ""
    ALLOWED_CHAT_IDS: str = ""
    
    DOWNLOAD_DIR: str = "./media"
    DOWNLOAD_WORKERS: int = 2
    MAX_RETRIES: int = 5
    DEFAULT_FOLDER: str = "outros"
    
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    @property
    def allowed_users(self) -> List[int]:
        return [int(x.strip()) for x in self.ALLOWED_USER_IDS.split(",") if x.strip()]
        
    @property
    def allowed_chats(self) -> List[int]:
        return [int(x.strip()) for x in self.ALLOWED_CHAT_IDS.split(",") if x.strip()]

settings = Settings()
