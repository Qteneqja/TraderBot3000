FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY requirements.lock ./
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.lock && useradd --create-home aegis
COPY app ./app
RUN pip install --no-deps .
COPY alembic.ini ./
COPY alembic ./alembic
RUN mkdir -p /app/data /app/model_artifacts && chown -R aegis:aegis /app
USER aegis
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
