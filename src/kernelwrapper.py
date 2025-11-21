import queue
import time
from threading import Event, Thread
from typing import Iterable
from uuid import uuid4

import zmq
from jupyter_client import KernelManager, session
from loguru import logger

from .config import get_settings
from .models import KernelResult, Status

config = get_settings()


class KernelWrapper:
    """
    Обертка над библиотечным классом kernel-а.
    """

    MIN_CODE_EXECUTION_TIME_S = 0.05

    def __init__(self) -> None:
        # для фиксирования портов отключаем кэширование таковых
        # https://github.com/jupyter/jupyter_client/issues/955#issuecomment-1621917317
        config.UPLOAD_DIR.mkdir(exist_ok=True)
        self.__kernel_manager = KernelManager(
            kernel_name="python", cache_ports=False, **config.connection_info
        )

        self.__kernel_manager.start_kernel(cwd=str(config.UPLOAD_DIR))
        info = self.__kernel_manager.client().get_connection_info()
        iopub_ip = f"{info['transport']}://{info['ip']}:{info['iopub_port']}"  # type: ignore
        shell_ip = f"{info['transport']}://{info['ip']}:{info['shell_port']}"  # type: ignore
        self.__key = info["key"]
        iopub_socket, self.__shell_socket = self.__setup_sockets(iopub_ip, shell_ip)
        self.__iopub_queue: queue.Queue[tuple] = queue.Queue()
        self.__disable = Event()
        self.__skip_execution = Event()
        self.__executor_status = Status.IDLE
        self.__status = Status.BUSY
        self.__define_jupyter_sockets()
        Thread(
            target=self.__start_listening_iopub, args=(iopub_socket,), daemon=True
        ).start()

    @property
    def jupyter_info(self) -> dict[str, str]:
        result = {}
        for key, value in self.__kernel_manager.client().get_connection_info().items():
            if isinstance(value, bytes):
                result[key] = str(value, "utf-8")
            else:
                result[key] = str(value)
        return result

    def clear_out(self):
        for _ in self.handle_results():
            pass

    def shutdown_kernel(self):
        self.__kernel_manager.shutdown_kernel()
        self.__disable.set()

    def restart_kernel(self):
        self.__kernel_manager.restart_kernel()

    def interrupt_kernel(self):
        self.__kernel_manager.interrupt_kernel()
        self.__skip_execution.set()

    def __define_jupyter_sockets(self):
        jupyter_info = self.__kernel_manager.client().get_connection_info()
        logger.info(f"Connection info: {jupyter_info}")
        iopub_ip = f"{jupyter_info['transport']}://{jupyter_info['ip']}:{jupyter_info['iopub_port']}"
        shell_ip = f"{jupyter_info['transport']}://{jupyter_info['ip']}:{jupyter_info['shell_port']}"
        self.key = jupyter_info["key"]
        (
            self.__iopub_socket,
            self.__shell_socket,
        ) = self.__setup_sockets(iopub_ip, shell_ip)

    def __setup_sockets(self, iopub_ip, shell_ip):
        context = zmq.Context()

        socket_iopub = context.socket(zmq.SUB)
        socket_iopub.connect(iopub_ip)
        socket_iopub.setsockopt_string(zmq.SUBSCRIBE, "")

        socket_send = context.socket(zmq.REQ)
        socket_send.connect(shell_ip)

        return socket_iopub, socket_send

    def __start_listening_iopub(self, iopub_socket):
        ses = session.Session(key=self.__key)
        while not self.__disable.is_set():
            message = ses.recv(iopub_socket, mode=zmq.NOBLOCK)
            if message != (None, None):
                if message[1]["msg_type"] == "status":
                    status = message[1]["content"]["execution_state"]
                    self.__status = Status.IDLE if status == "idle" else Status.BUSY

                self.__iopub_queue.put(message)
            time.sleep(self.MIN_CODE_EXECUTION_TIME_S / 10)

    def get_status(self) -> Status:
        return self.__status

    def get_ex_status(self) -> Status:
        return self.__executor_status

    def __await_task(self):
        while self.__executor_status == Status.BUSY:
            time.sleep(self.MIN_CODE_EXECUTION_TIME_S)

    def execute_code(self, code: str):
        """
        Исполнение кода
        code - строка кода получаемая из клиента

        """
        self.__status = Status.BUSY
        self.__await_task()
        self.__executor_status = Status.BUSY
        ses = session.Session(key=self.__key)
        self.__executor_status = Status.BUSY
        ses.send(
            self.__shell_socket,
            "execute_request",
            content={
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,  # todo: add later
                "stop_on_error": False,
            },
            track=True,
            header={
                "msg_id": str(uuid4()),
                "username": "root",
                "session": ses.session,
                "msg_type": "execute_request",
                "version": "5.0",
            },
        )
        ses.recv(self.__shell_socket, mode=zmq.BLOCKY)
        time.sleep(self.MIN_CODE_EXECUTION_TIME_S)
        self.__executor_status = Status.IDLE

    def handle_results(self) -> Iterable[KernelResult]:
        """
        Вытаскивает из очереди сообщения, которые отправляет kernel.
        """
        while not self.__iopub_queue.empty() and not self.__skip_execution.is_set():
            kernel_result = KernelResult(
                msg_content={},
                msg_type="",
            )
            message = self.__iopub_queue.get_nowait()
            if message[1]["msg_type"] in ["status", "execute_input"]:
                continue
            kernel_result.msg_content = message[1]["content"]
            kernel_result.msg_type = message[1]["msg_type"]
            logger.info(f"handle result: {str(kernel_result)[:200]}")
            yield kernel_result
        self.__skip_execution.clear()

    def preload_cells(self):
        self.__preload_cell("from loguru import logger")

    def __preload_cell(self, command: str) -> None:
        logger.info(f"Preload command: {command}")
        self.execute_code(command)
        for kernel_result in self.handle_results():
            logger.info(f"Result: {kernel_result.msg_content}")
