import asyncio

import socketio
from loguru import logger


class SocketIOClient:
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self.__sio = socketio.AsyncClient()
        self.__server_url = server_url
        self._setup_handlers()
        self._output_queue = asyncio.Queue()

    def set_server_url(self, server_url: str) -> None:
        self.__server_url = server_url

    def _setup_handlers(self):
        @self.__sio.event
        async def connect():
            logger.info("Connected to server")

        @self.__sio.event
        async def disconnect():
            logger.info("Disconnected from server")

        @self.__sio.on("output")
        async def on_kernel_message(data):
            await self._output_queue.put(data)

    def connected(self):
        return self.__sio.connected

    async def connect(self):
        await self.__sio.connect(self.__server_url, transports=["websocket"])

    async def disconnect(self):
        await self.__sio.disconnect()

    async def _send_command(self, command: str, **kwargs):
        """Отправляет команду ядру"""
        message = {"command": command, **kwargs}
        logger.info(f"Sending command: {message}")  # noqa: PIE803
        await self.__sio.emit("command", message)

    async def execute_command(self, command: str) -> None:
        """Метод отправляет код на запуск"""
        await self._send_command("execute", code=command)

    async def get_output(self) -> dict | None:
        try:
            return self._output_queue.get_nowait()
        except asyncio.QueueEmpty:
            return
