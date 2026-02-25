from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "ITVE Donor API"
    VERSION: str = "1.0.0"
    
    # Database Configuration
    MONGO_URL: str = Field(..., alias="MONGO_URL")
    DB_NAME: str = "ITVE_Database"

    # Security Configuration
    # These fields automatically fetch values from the .env file using the alias
    SECRET_KEY: str = Field(alias="JWT_SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", alias="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Business Logic Configuration
    ADMIN_SECRET_CODE: str
    UPLOAD_DIR: str = "uploads"
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}

    # This configuration tells Pydantic to read variables from the .env file
    # extra="ignore" ensures that if there are extra variables in .env, it won't crash
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Create a global instance to be imported across the application
settings = Settings()