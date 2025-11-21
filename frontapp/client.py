import asyncio

import aiohttp
import socketio
from loguru import logger


class SocketIOClient:
    def __init__(self, server_url: str = "http://127.0.0.1"):
        self.__sio = socketio.AsyncClient()
        self.__server_url = server_url
        self._setup_handlers()
        self._output_queue = asyncio.Queue()
    
    @property
    def server_url(self) -> str:
        return self.__server_url

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

    async def check_server_port_for_host(self, default_port=8000) -> int:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.__server_url}:{default_port}/service/check"
                ) as response:
                    assert response.status == 200
            except (AssertionError, aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
                pass
            else:
                return default_port

            for port in range(5000, 9000):
                try:
                    async with session.get(
                        f"{self.__server_url}:{port}/service/check"
                    ) as response:
                        assert response.status == 200
                except (AssertionError, aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
                    pass
                else:
                    return port
        raise Exception("No server running on this host adress")

    async def connect(self):
        if len(self.__server_url.split(":")) == 2:
            port = await self.check_server_port_for_host()
            self.__server_url += f":{port}"
        logger.info(f"{self.__server_url=}")
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
