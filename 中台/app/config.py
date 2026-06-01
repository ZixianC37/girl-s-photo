from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    dingtalk_app_key: str = ""
    dingtalk_app_secret: str = ""
    dingtalk_robot_code: str = ""
    wecom_corp_id: str = ""
    wecom_agent_id: str = ""
    wecom_secret: str = ""
    admin_token: str = "changeme"
    database_url: str = "sqlite:///./middleware.db"

    class Config:
        env_file = ".env"

settings = Settings()
