"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure AI Foundry
    foundry_project_endpoint: str = ""
    azure_ai_model_deployment_name: str = "gpt-4o"
    foundry_toolbox_endpoint: str = ""

    # MCP Server
    mcp_server_url: str = "http://localhost:8000/mcp/"

    # API-Football v3
    football_api_key: str = ""
    football_api_base_url: str = "https://v3.football.api-sports.io"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/worldcup"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
