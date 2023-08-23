FROM python:3.10

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml .
COPY poetry.toml .
COPY poetry.lock .

RUN poetry install

COPY . .

ENTRYPOINT ["python"]

CMD ["main.py"]
