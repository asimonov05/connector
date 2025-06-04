import base64
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

from loguru import logger


def remove_ansi_escape(text: str) -> str:
    """Удаляет ANSI escape-последовательности из строки."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def parse_text(jupyter_output: dict | None) -> str | None:
    if not isinstance(jupyter_output, dict):
        return
    output = None
    content = jupyter_output.get("content", {})
    text = content.get("data", {}).get("text/plain")
    stdout = content.get("text")
    traceback = content.get("traceback")
    if text:
        output = text
    if stdout:
        output = stdout
    if traceback:
        output = "\n".join(traceback)
    if output:
        return remove_ansi_escape(output)


def is_execution_ended(jupyter_output: dict | None) -> bool:
    if not jupyter_output:
        return
    return jupyter_output.get("command", "") == "notebook-end"


def show_image(jupyter_output: dict | None) -> Path | None:
    if not isinstance(jupyter_output, dict):
        return
    if not (
        image := jupyter_output.get("content", {}).get("data", {}).get("image/png")
    ):
        logger.info(f"check for image {image}")
        return
    file_path = Path(os.path.abspath(__file__)).parent
    image_file_path = file_path / Path("files")
    image_file_path.mkdir(parents=True, exist_ok=True)
    image_file_path = image_file_path / f"{uuid.uuid4()}.png"
    binary_data = base64.b64decode(image)
    with image_file_path.open("wb") as file:
        file.write(binary_data)
    if sys.platform == "darwin":
        subprocess.run(["open", image_file_path])
    elif sys.platform == "win32":
        os.startfile(image_file_path)
    elif sys.platform == "linux":
        subprocess.run(["xdg-open", image_file_path])
    return image_file_path
