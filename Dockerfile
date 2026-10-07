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
# Inside the data volume so logs survive container updates
ENV LOG_DIR=/app/data/logs

# Set by the GitHub Action; shown in the app and returned by /api/version
ARG APP_VERSION=dev
ARG BUILD_DATE=
ENV APP_VERSION=$APP_VERSION
ENV BUILD_DATE=$BUILD_DATE

EXPOSE 8081

CMD ["python", "backend/app.py"]