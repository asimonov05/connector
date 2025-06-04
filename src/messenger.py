import socketio
from loguru import logger

from src.sender import Sender

from .config import get_settings
from .handler import Handler
from .kernelwrapper import KernelWrapper

settings = get_settings()


class Messenger:
    def __init__(self, kernel: KernelWrapper) -> None:
        self.sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
        self.sender = Sender(self.sio)
        self.sender.start()
        self.handler = Handler(self.sender, kernel)
        self.__setup_socketio_handlers()

    def _input_prompt_format(self, code: str) -> str:
        splitted_command = code.split("\n")
        command_output = ">>> " + splitted_command[0]
        if len(splitted_command) > 1:
            for line in splitted_command[1:]:
                command_output += "\n... " + line
        return command_output

    def __setup_socketio_handlers(self) -> None:
        @self.sio.on("connect")
        def on_connect(sid, environ):
            logger.info(f"Client connected {sid}")

        @self.sio.on("disconnect")
        def on_disconnect(sid):
            logger.info(f"Client disconnected {sid}")

        @self.sio.on("command")
        async def on_message(sid, message: dict):
            if not isinstance(message, dict):
                return

            logger.info(f"Received message: {message}")
            command = message.get("command", "")
            logger.info(f"Executing {command}")

            if command == "restart":
                self.handler.restart()
            elif command == "shutdown":
                self.handler.shutdown()
            elif command == "interrupt":
                self.handler.interrupt()
            elif command == "execute":
                code = message["code"]
                await self.sio.emit(
                    "output",
                    data={"content": {"text": self._input_prompt_format(code)}},
                )
                self.handler.execute(code)
            elif command == "exit":
                self.handler.shutdown()
                self.sio.disconnect()
            await self.sio.emit("output", data={"status": "operation completed"})

    async def stop(self):
        await self.sender.stop()
        self.handler.shutdown()
