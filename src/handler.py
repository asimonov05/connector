import time
from threading import Event, Thread

import zmq
from loguru import logger

from src.sender import Sender

from .config import get_settings
from .kernelwrapper import KernelWrapper
from .models import Status

config = get_settings()


class Handler:
    def __init__(self, sender: Sender, kernel: KernelWrapper) -> None:
        self.__sender = sender
        self.__kernel = kernel
        self.__skip_execution = Event()
        self.__execution_thread: Thread | None = None

    def restart(self):
        self.__kernel.restart_kernel()
        self.__kernel.clear_out()
        self.__kernel.preload_cells()
        self.__sender.send_message({"command": "notebook-restart"})

    def shutdown(self):
        self.__skip_execution.set()
        self.__kernel.interrupt_kernel()
        if self.__execution_thread is not None:
            self.__execution_thread.join()
        self.__kernel.clear_out()
        self.__skip_execution.clear()
        self.__kernel.shutdown_kernel()
        self.__sender.send_message({"command": "notebook-shutdown"})
        logger.info("Kernel disabled.")

    def interrupt(self):
        self.__skip_execution.set()
        self.__kernel.interrupt_kernel()
        if self.__execution_thread is not None:
            self.__execution_thread.join()
        self.__kernel.clear_out()
        self.__skip_execution.clear()
        self.__sender.send_message({"command": "notebook-interrupt"})

    def execute(self, code: str):
        logger.info(
            f"Kernel execute code: {code}; kernel status: {self.__kernel.get_ex_status()}"
        )
        while self.__kernel.get_ex_status() == Status.BUSY:
            time.sleep(0.1)
        Thread(target=self.__kernel.execute_code, args=(code,), daemon=True).start()
        self.__execution_thread = Thread(target=self.__handle_code, daemon=True)
        self.__execution_thread.start()
        time.sleep(self.__kernel.MIN_CODE_EXECUTION_TIME_S)
        return self.__execution_thread

    def send_jupyter_connection_info(self, message_id: int):
        jupyter_info = self.__kernel.jupyter_info
        self.__sender.send_message(
            {
                "command": "notebook-jupyter_connection_info",
                "content": jupyter_info,
                "id": message_id,
            }
        )
        logger.info(f"Sent JupyterClient connection info: {jupyter_info}")

    def __handle_code(self):
        while self.__kernel.get_status() == Status.BUSY:
            for kernel_result in self.__kernel.handle_results():
                logger.info(f"handling {kernel_result}")
                if self.__skip_execution.is_set():
                    return
                self.__sender.send_message(
                    {
                        "command": "notebook-upd",
                        **(kernel_result.json()),
                    }
                )
                logger.info(f"send to middle {kernel_result}")
        self.__sender.send_message({"command": "notebook-end"})
