from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class JupyterClientInfo(BaseSettings):
    transport: str = Field("tcp", env="JUPYTER_SHELL_TRANSPORT")
    ip: str = Field("127.0.0.1", env="JUPYTER_SHELL_HOST")
    shell_port: int = Field(4023, env="JUPYTER_SHELL_PORT")
    iopub_port: int = Field(4024, env="JUPYTER_IOPUB_PORT")
    stdin_port: int = Field(4025, env="JUPYTER_STDIN_PORT")
    hb_port: int | None = Field(4026, env="JUPYTER_HB_PORT")
    control_port: int | None = Field(4027, env="JUPYTER_CONTROL_PORT")


class Config(BaseSettings):
    SOCKETIO_HOST: str = "0.0.0.0"
    SOCKETIO_PORT: int = 8000
    jupyter_client_info: JupyterClientInfo = JupyterClientInfo()  # type: ignore[call-arg]
    UPLOAD_DIR: Path = Path("/user")

    @property
    def connection_info(self) -> dict:
        return self.jupyter_client_info.dict(exclude_none=True)


@lru_cache  # we need to create an object only once
def get_settings() -> Config:
    return Config()
