FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir -e .
COPY docs/ ./docs/
COPY data/ ./data/
RUN useradd -m -u 10001 retail && chown -R retail:retail /app
USER retail
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "retailmind.api:app", "--host", "0.0.0.0", "--port", "8000"]
