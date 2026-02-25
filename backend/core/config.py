from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    FMP_API_KEY: str = ""
    PAYSTACK_SECRET_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    RESEND_API_KEY: str = ""


settings = Settings()
