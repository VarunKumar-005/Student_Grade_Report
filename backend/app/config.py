from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Student Mark Attainment System'
    env: str = 'dev'

    database_url: str = 'sqlite:///./student_grade_report.db'
    jwt_secret: str = 'change-this-secret'
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 120


settings = Settings()
