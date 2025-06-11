
FROM python:3.11.0-slim-bullseye

ARG POETRY_HOME=/etc/poetry

USER root

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libxt6 git unzip curl tini gcc && \
    pip install poetry==1.6.1 && \
    apt-get remove -y curl && \
    apt-get remove -y --purge build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /
COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false && \
    poetry install --without front --no-interaction --no-cache && \
    rm -rf ~/.cache ~/.config/pypoetry/auth.toml

COPY ./backend.py ./main.py
COPY ./src ./src

CMD ["python3", "main.py"]
