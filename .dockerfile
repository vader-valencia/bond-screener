FROM python:3.8

WORKDIR /app

COPY pyproject.toml .
COPY poetry.lock .

RUN pip install poetry
RUN poetry install

COPY . .

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
