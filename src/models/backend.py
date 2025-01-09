from pydantic import BaseModel, EmailStr, Field

from utils.constants.constant import DatabaseType


class ClientCreate(BaseModel):
    client_name: str | None = None
    client_email: str


class DatabaseConfig(BaseModel):
    db_name: str = Field(..., description="Name of the database")
    db_type: DatabaseType = Field(..., description="Type of the database")
    db_host: str = Field(..., description="Database connection host")
    db_port: int = Field(..., description="Database connection port")
    db_username: str = Field(..., description="Database username")
    db_password: str = Field(..., description="Database password")


class DatabaseCreate(BaseModel):
    client_email: EmailStr
    database_config: DatabaseConfig


class SQLRequest(BaseModel):
    client_name: str | None = None
    client_email: EmailStr
    database_name: str
    files: list


class BedrockRequest(BaseModel):
    prompt: str
    system: str | None = None
    max_tokens: int | None = 1000
    temperature: float | None = 0.7


class BatchBedrockRequest(BaseModel):
    prompts: list[str]
    system: str | None = None
    max_tokens: int | None = 1000
    temperature: float | None = 0.7
