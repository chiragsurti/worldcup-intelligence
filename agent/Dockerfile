FROM python:3.12-slim

WORKDIR /app

COPY agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY config/ ./config/
COPY agent/ ./agent/

ENV PYTHONPATH=/app
EXPOSE 8088

CMD ["python", "agent/main.py"]
