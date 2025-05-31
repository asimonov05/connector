import sys
import asyncio

from PyQt5.QtWidgets import QApplication

from frontapp.terminal_ui import PythonTerminal


def main():
    app = QApplication(sys.argv)
    terminal = PythonTerminal()
    terminal.start_client()
    terminal.show()
    sys.exit(app.exec_())
    terminal.stop_client()


if __name__ == "__main__":
    asyncio.run(main())
