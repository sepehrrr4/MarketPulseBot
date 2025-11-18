from pydantic_settings import BaseSettings, SettingsConfigDict

class BotSettings(BaseSettings):
    """
    Main configuration for the Bot and API services.
    These values are automatically loaded from the .env file or environment variables.
    """

    # Telegram Bot Token obtained from BotFather
    # No default value (must be provided)
    BOT_TOKEN: str

    # The Channel ID required for forced subscription check
    # For public channels: @YourChannelName
    # For private channels: -100... (Numeric ID)
    CHANNEL_ID: str

    # The URL of the running Price API
    # Default is set to localhost port 8000
    PRICE_API_URL: str = "http://127.0.0.1:8000/prices"

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"  # Ignore extra variables in .env that are not defined here
    )

# Create a settings instance to be used throughout the application
settings = BotSettings()