# Connector

Programm for connecting to terminal on 'server' terminal from 'client' via LAN

### Quick start
1. Create virtual enviroment (using virtualenv)
```bash
pip install virtualenv # если не установлено
python -m virtualenv venv
```
2. Activate venv
```bash
source venv/bin/activate # для linux систем
venv/Scripts/activate.bat # для Windows 7
```
3. Setup project
```bash
pip install poetry==1.6.1
poetry install
```
4. Run
```bash
python backend.py # для запуска сервера
python frontend.py # для запуска GUI оболочки
```

### Developing
#### Formatting
Use `make format` to prettify code
