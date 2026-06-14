FROM python:3.12-slim

WORKDIR /app

COPY mcp_server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY config/ ./config/
COPY data/ ./data/
COPY mcp_server/ ./mcp_server/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["python", "mcp_server/server.py"]
