FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

ENV HOST=0.0.0.0
ENV PORT=8081
ENV DEBUG=False
ENV DATA_DIR=/app/data

EXPOSE 8081

CMD ["python", "backend/app.py"]