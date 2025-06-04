import re


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
