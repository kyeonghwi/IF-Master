from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ifmaster:ifmaster@localhost:5432/ifmaster"
    jwt_secret: str = "change-me"
    demo_username: str = "test_admin"
    demo_password: str = "demo1234"
    frontend_url: str = "https://if-master.vercel.app"
    cookie_secure: bool = False  # True in production (HTTPS)

    class Config:
        env_file = ".env"


settings = Settings()
