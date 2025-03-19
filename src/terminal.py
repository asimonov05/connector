import asyncio
import subprocess

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


class InteractiveShell:
    """
    Класс предназначенный для работы с терминалов в интерактивном режиме

    Интерфейс предусматривает ввод входных данных через соответствующую очередь
        `input_queue`
    Выходные данные попадают в очередь
        `output_queue`
    """

    def __init__(self, terminal_name: str = "bash"):
        self.process = None
        self.terminal_name = terminal_name

    async def start(self, input_queue: asyncio.Queue, output_queue: asyncio.Queue):
        """
        Запуск терминала в интерактивном режиме с прокидыванием
            stdin, stdout, stderr через туннели с их обработкой

        stdin пишется из данных, поступаемых через очередь `input_queue`
        stdout, stderr записываются в очередь `output_queue`
        """
        self.process = await asyncio.create_subprocess_exec(
            f"/bin/{self.terminal_name}",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=False,
        )

        self.stdout_task = asyncio.create_task(self.read_stdout(output_queue))
        self.stderr_task = asyncio.create_task(self.read_stderr(output_queue))
        self.input_task = asyncio.create_task(self.handle_input(input_queue))

    async def shutdown(self) -> None:
        """
        Завершение терминала, а также всех сопроводительных процессов
        """
        await asyncio.gather(self.stdout_task, self.stderr_task)
        self.input_task.cancel()
        try:
            await self.input_task
        except asyncio.CancelledError:
            pass

        self.process.stdin.close()
        await self.process.wait()

    async def handle_input(self, input_queue: asyncio.Queue) -> None:
        """
        Метод для прокидывания входных данных из очереди в запущенный терминал
        """
        while True:
            command = await input_queue.get()
            if command.lower() == "exit":
                print("Exiting shell.")
                self.process.stdin.write("exit\n".encode())
                await self.process.stdin.drain()
                break
            self.process.stdin.write((command + "\n").encode())
            await self.process.stdin.drain()

    async def read_stdout(self, output_queue: asyncio.Queue) -> None:
        """
        Метод для прокидывания выходных данных в очередь
        """
        while True:
            chunk = await self.process.stdout.read(1024)
            if not chunk:
                output_queue.put_nowait(None)
                break
            output_queue.put_nowait(chunk.decode("utf-8"))

    async def read_stderr(self, output_queue: asyncio.Queue) -> None:
        """
        Метод для прокидывания выходных данных ошибок в очередь
        """
        while True:
            chunk = await self.process.stderr.read(1024)
            if not chunk:
                output_queue.put_nowait(None)
                break
            output_queue.put_nowait(f"Error: {chunk.decode('utf-8')}")


class MockInteract:
    """
    Класс для тестирования работы терминала через пользовательский ввод в stdin
    """

    def __init__(self):
        self.session = PromptSession()

    async def run(self, input_queue, output_queue):
        self.input_reader = asyncio.create_task(self.read_input(input_queue))
        self.output_reader = asyncio.create_task(self.handle_output(output_queue))

    async def read_input(self, input_queue):
        while True:
            with patch_stdout():
                command = await self.session.prompt_async(">>> ")
                await input_queue.put(command)

    async def handle_output(self, output_queue):
        while True:
            output = await output_queue.get()
            if output is None:
                break
            print(output, end="")

    async def shutdown(self):
        if not self.input_reader.done():
            self.input_reader.cancel()
        if not self.output_reader.done():
            self.output_reader.cancel()
        try:
            await self.input_reader
        except asyncio.CancelledError:
            pass
        try:
            await self.output_reader
        except asyncio.CancelledError:
            pass


async def main():
    input_queue = asyncio.Queue()
    output_queue = asyncio.Queue()
    shell = InteractiveShell(terminal_name="zsh")
    interaction = MockInteract()

    await interaction.run(input_queue, output_queue)
    await shell.start(input_queue, output_queue)
    await shell.shutdown()
    await interaction.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
