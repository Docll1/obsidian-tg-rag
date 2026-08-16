FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY data/sample ./data/sample

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "src.bot"]
