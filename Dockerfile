FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy application code
COPY backend ./backend
COPY frontend ./frontend

# Azure/App Service configuration
ENV HOST=0.0.0.0
ENV PORT=8081
ENV DEBUG=False
ENV DATA_DIR=/home/bingopoker-data

# Create the persistent data directory
RUN mkdir -p /home/bingopoker-data

EXPOSE 8081

# Start BingoPoker
CMD ["python", "backend/app.py"]