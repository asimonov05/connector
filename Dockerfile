
FROM python:3.11.12-slim-bullseye

ARG POETRY_HOME=/etc/poetry

USER root

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libxt6 git unzip curl tini && \
    curl -sSL https://install.python-poetry.org | POETRY_HOME=${POETRY_HOME} python - --version 1.8.2 && \
    apt-get remove -y curl && \
    apt-get remove -y --purge build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="${PATH}:${POETRY_HOME}/bin:/home/engee/.local/bin"

WORKDIR /
COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-cache && \
    rm -rf ~/.cache ~/.config/pypoetry/auth.toml

COPY ./backend.py ./main.py
COPY ./src ./src

CMD ["python3", "main.py"]
