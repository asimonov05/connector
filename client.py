import socketio
from loguru import logger
import asyncio


class SocketIOClient:
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        self.sio = socketio.AsyncClient()
        self.server_url = server_url
        self.setup_handlers()

    def setup_handlers(self):
        @self.sio.event
        async def connect():
            logger.info("Connected to server")

        @self.sio.event
        async def disconnect():
            logger.info("Disconnected from server")

        @self.sio.on("output")
        async def on_kernel_message(data):
            logger.info(f"Received from kernel: {data}")

    async def connect_to_server(self):
        try:
            await self.sio.connect(self.server_url, transports=["websocket"])
            # await self.sio.wait()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.sio.disconnect()

    async def send_command(self, command: str, **kwargs):
        """Отправляет команду ядру"""
        message = {"command": command, **kwargs}
        logger.info(f"Sending command: {message}")
        await self.sio.emit("command", message)

    async def interactive_session(self):
        """Интерактивная сессия для отправки команд"""
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)
                await self.send_command("execute", code=user_input)

                # if user_input.lower() == "exit":
                #     await self.send_command("exit")
                #     await self.sio.disconnect()
                #     break
                # elif user_input.lower() == "help":
                #     print("Available commands:")
                #     print("  execute <code> - Execute Python code")
                #     print("  restart - Restart kernel")
                #     print("  interrupt - Interrupt execution")
                #     print("  shutdown - Shutdown kernel")
                #     print("  exit - Disconnect and exit")
                # elif user_input.startswith("execute "):
                #     code = user_input[8:]
                #     await self.send_command("execute", code=code)
                # elif user_input == "restart":
                #     await self.send_command("restart")
                # elif user_input == "interrupt":
                #     await self.send_command("interrupt")
                # elif user_input == "shutdown":
                #     await self.send_command("shutdown")
                # else:
                #     print("Unknown command. Type 'help' for options.")

            except KeyboardInterrupt:
                await self.send_command("exit")
                await self.sio.disconnect()
                break


async def main():
    client = SocketIOClient()
    await client.connect_to_server()
    await client.interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
