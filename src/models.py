from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    BUSY: str = "busy"
    IDLE: str = "idle"


@dataclass
class KernelResult:
    """
    text_plain - text_execution_output for all stdout message from cell except for
    logger messages, which are contained date-time marker.

    image_png - non_text_plain we usually store info about images

    json_plotly - a list of dictionaries with info for plotly interactive plots
    """

    msg_content: dict
    msg_type: str

    def json(self) -> dict:
        return {
            "content": self.msg_content,
            "msg_type": self.msg_type,
        }
