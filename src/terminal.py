import asyncio

import sys
import os
from subprocess import PIPE, STDOUT, Popen
from loguru import logger
from enum import Enum


class States(Enum):
    IDLE = 1
    RUNNING = 2


class LocalShell:
    def __init__(self) -> None:
        self.__writer: asyncio.Task | None = None
        self.__reader: asyncio.Task | None = None
        self.__process: Popen | None = None
        self.state = States.IDLE

    async def _writer_process(self, output_queue: asyncio.Queue) -> None:
        logger.info("writer active")
        while True:
            data = self.__process.stdout.read(1).decode("utf-8")
            logger.info(data)
            if not data:
                await asyncio.sleep(0.01)
                continue
            await output_queue.put_nowait(data)

    def _write_to_process(self, process: Popen, message: str):
        process.stdin.write(message.encode())
        process.stdin.flush()

    async def _reader_process(self, input_queue: asyncio.Queue) -> None:
        logger.info("reader active")
        while True:
            data = await input_queue.get()
            logger.info(data)
            if not data or len(data) > 1:
                # logger.warning(f"Incorrect queue arg {data=}")
                await asyncio.sleep(0.01)
                continue
            self._write_to_process(self.__process, data)

    async def run(
        self, input_queue: asyncio.Queue, output_queue: asyncio.Queue
    ) -> None:
        if self.__writer or self.__reader:
            raise ValueError("Process is running")

        env = os.environ.copy()
        self.__process = Popen(
            "/bin/bash",
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
            shell=True,
            env=env,
        )
        self.__writer = asyncio.create_task(self._writer_process(output_queue))
        self.__reader = asyncio.create_task(self._reader_process(input_queue))
        self.state = States.RUNNING

    async def terminate(self) -> None:
        if self.state != States.RUNNING:
            return
        self.__process.kill()
        if self.__writer:
            await self.__writer
        if self.__reader:
            await self.__reader
        self.state = States.IDLE


class MockInteract:
    async def inp(self, q: asyncio.Queue) -> None:
        while True:
            s = input()
            for letter in s:
                await q.put_nowait(letter)
                await asyncio.sleep(0.01)

    async def out(self, q: asyncio.Queue) -> None:
        while True:
            letter = await q.get_nowait()
            await asyncio.sleep(0.01)
            logger.info(letter)

    async def main(self):
        shell = LocalShell()
        inp_q = asyncio.Queue()
        out_q = asyncio.Queue()
        t1 = asyncio.create_task(self.inp(inp_q))
        t2 = asyncio.create_task(self.out(out_q))
        await shell.run(inp_q, out_q)
        logger.info(f"{shell.state}")
        await t1
        await t2
        await shell.terminate()


mock = MockInteract()
asyncio.run(mock.main())
