import asyncio

import socketio
from loguru import logger


class Sender:
    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio
        self.__task: asyncio.Task | None = None
        self._queue = asyncio.Queue()

    def start(self) -> None:
        loop = asyncio.get_event_loop()
        self.__task = asyncio.ensure_future(self.__sender(), loop=loop)

    async def stop(self) -> None:
        if not self.__task or self.__task.done():
            return
        self.__task.cancel()
        try:
            await self.__task
        except asyncio.CancelledError:
            pass

    def send_message(self, data: dict) -> None:
        logger.info(f"Sending message from kernel: {data}")
        self._queue.put_nowait(data)

    async def __sender(self) -> None:
        while True:
            msg = await self._queue.get()
            try:
                await self.sio.emit("output", data=msg)
            except Exception as e:
                logger.opt(exception=e).warning(f"Message could't send {msg=}")
