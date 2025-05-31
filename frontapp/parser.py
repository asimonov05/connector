def parse_text(jupyter_output: dict | None) -> str | None:
    if not isinstance(jupyter_output, dict):
        return
    text = jupyter_output.get("content", {}).get("data", {}).get("text/plain")
    stdout = jupyter_output.get("content", {}).get("text")
    return text or stdout


def is_execution_ended(jupyter_output: dict | None) -> bool:
    if not jupyter_output:
        return
    return jupyter_output.get("command", "") == "notebook-end"
