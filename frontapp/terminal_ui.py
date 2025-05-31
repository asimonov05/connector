import asyncio
from loguru import logger
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from frontapp.highlight import PythonHighlighter
from frontapp.client import SocketIOClient
from queue import Queue, Empty
from threading import Thread, Event
from frontapp.parser import parse_text, is_execution_ended
from contextlib import suppress


class PythonTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Terminal")
        self.setGeometry(100, 100, 800, 600)

        self.initUI()
        self.history = []
        self.history_index = -1
        self.__client = SocketIOClient()
        self.__code_queue = Queue()
        self.__client_connection: Thread | None = None
        self.__connected = False
        self.__connect_lock = Event()
        self.__execute_lock = Event()

    def initUI(self):
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Layout
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # URL input section
        url_layout = QHBoxLayout()

        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setText("http://127.0.0.1:8000")
        self.url_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, Courier New, monospace;
                font-size: 12pt;
                border: 1px solid #3E3E3E;
                padding: 5px;
            }
        """
        )

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3E3E3E;
                color: #D4D4D4;
                border: 1px solid #5E5E5E;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
        """
        )
        self.connect_btn.clicked.connect(self._connect_event)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.connect_btn)
        layout.addLayout(url_layout)

        # Output area
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, Courier New, monospace;
                font-size: 12pt;
            }
        """
        )
        tab_width = self.output_area.fontMetrics().width(" ") * 3
        self.output_area.setTabStopDistance(tab_width)

        # Scroll area for output
        scroll = QScrollArea()
        scroll.setWidget(self.output_area)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        # Input area
        self.input_area = QTextEdit()
        self.input_area.setMaximumHeight(100)
        tab_width = self.input_area.fontMetrics().width(" ") * 3
        self.input_area.setTabStopDistance(tab_width)
        self.input_area.setStyleSheet(
            """
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas, Courier New, monospace;
                font-size: 12pt;
                border: 1px solid #3E3E3E;
            }
        """
        )

        # Add syntax highlighting to input area
        self.highlighter = PythonHighlighter(self.input_area.document())

        # Input controls
        input_controls = QHBoxLayout()

        # Execute button
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3E3E3E;
                color: #D4D4D4;
                border: 1px solid #5E5E5E;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
        """
        )
        self.execute_btn.clicked.connect(self.execute_command)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(self.execute_btn.styleSheet())
        self.clear_btn.clicked.connect(self.clear_input)
        self.execute_btn.setEnabled(False)

        input_controls.addWidget(self.execute_btn)
        input_controls.addWidget(self.clear_btn)

        layout.addLayout(input_controls)
        layout.addWidget(self.input_area)

        # Set focus to input area
        self.input_area.setFocus()

    def _connect_event(self) -> None:
        self.__connect_lock.clear()
        if not self.__client.connected():
            self.__client.set_server_url(self.url_input.text().strip())
            self.__connected = True
            self.__connect_lock.wait()
            if self.__connected:
                self._connected_event()
            else:
                self._add_output("Can't connect to server")
        else:
            self.__connected = False
            self.__connect_lock.wait()
            if not self.__connected:
                self._disconnect_event()
            else:
                self._add_output("Can't disconnect from server")

    def _connected_event(self):
        self.connect_btn.setText("Disconnect")
        self.url_input.setEnabled(False)
        self.execute_btn.setEnabled(True)
        self.output_area.clear()

    def _disconnect_event(self):
        self.connect_btn.setText("Connect")
        self.url_input.setEnabled(True)
        self.execute_btn.setEnabled(False)

    def start_client(self) -> None:
        if self.__client_connection and self.__client_connection.is_alive():
            raise RuntimeError("Connection already set")
        self.__client_connection = Thread(
            target=asyncio.run, args=(self._client_connection(),), daemon=True
        )
        self.__running = True
        self.__client_connection.start()

    def stop_client(self) -> None:
        if self.__client_connection and not self.__client_connection.is_alive():
            return
        self.__running = False
        try:
            self.__client_connection.join(2)
        except RuntimeError:
            logger.warning("Can't stop thread")

    async def _client_connection(self) -> None:
        while self.__running:
            if not self.__client.connected():
                await asyncio.sleep(0.2)
            if self.__connected and not self.__client.connected():
                try:
                    await self.__client.connect()
                except Exception:
                    self.__connected = False
                    raise
                finally:
                    if not self.__connect_lock.is_set():
                        self.__connect_lock.set()
            elif not self.__connected and self.__client.connected():
                try:
                    await self.__client.disconnect()
                except Exception:
                    self.__connected = True
                    raise
                finally:
                    if not self.__connect_lock.is_set():
                        self.__connect_lock.set()
            try:
                command = await self.__client.get_output()
                out = parse_text(command)
                if out:
                    self._add_output(out)
                elif is_execution_ended(command) and not self.__execute_lock.is_set():
                    self.__execute_lock.set()
                with suppress(Empty):
                    code = self.__code_queue.get_nowait()
                    if code:
                        await self.__client.execute_command(code)
            except Exception as e:  # noqa: PIE786
                logger.exception(e)
            await asyncio.sleep(0.01)
        if self.__client.connected():
            await self.disconnect()
            self.__connected = False

    def clear_input(self):
        self.input_area.clear()

    def _execute_command_sync(self, command: str) -> None:
        self.__execute_lock.clear()
        self.__code_queue.put(command)
        self.__execute_lock.wait()

    def _add_output(self, output: str) -> None:
        if output:
            self.output_area.append(output)
        self.output_area.moveCursor(QTextCursor.End)
        scrollbar = self.output_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def execute_command(self):
        command = self.input_area.toPlainText().strip()

        if not command:
            return

        self.history.append(command)
        self.history_index = len(self.history)

        splitted_command = command.split("\n")
        command_output = ">>> " + splitted_command[0]
        if len(splitted_command) > 1:
            for line in splitted_command[1:]:
                command_output += "\n... " + line
        self.output_area.append(command_output)

        if command.strip().lower() in ("exit", "quit", "exit()", "quit()"):
            self.close()
            return

        self.input_area.clear()
        self._execute_command_sync(command)
