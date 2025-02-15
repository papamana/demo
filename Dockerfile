# Use Python 3.9 slim as base image
FROM python:3.9-slim-buster

# Set working directory
WORKDIR /app

# Install system dependencies required for Pillow and OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a directory for logs
RUN mkdir -p logs && chmod 777 logs

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV HOST=0.0.0.0

# Run the application
CMD ["python", "app.py"]