FROM ubuntu:24.10
LABEL org.opencontainers.image.authors='Oleh Rybalchenko rv.oleg.ua@gmail.com'

COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
RUN mkdir /app
WORKDIR /app

#ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH="/app/.venv/bin:/app"
#ENV UV_PROJECT_ENVIRONMENT=/usr/bin/

COPY ./uv.lock /app/uv.lock
COPY ./pyproject.toml /app/pyproject.toml
RUN uv sync --locked
COPY . /app
CMD ["uv", "run", "python3", "app.py"]