# Use multi-stage build for Node frontend and Python backend

# Stage 1: Build the frontend
FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Build the backend
FROM python:3.11-slim AS backend-build

# Install uv
RUN pip install uv

WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY backend/pyproject.toml backend/
COPY backend/main.py backend/

# Install dependencies with uv
RUN cd backend && uv pip install --system -e . && uv pip install --system bcrypt

# Stage 3: Final image
FROM python:3.11-slim

# Install uv
RUN pip install uv

# Install Node.js for serving static files (if needed)
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend
COPY backend/ backend/

# Copy frontend build
COPY --from=frontend-build /app/frontend/out /app/static

# Copy catalog.json and .env
COPY catalog.json /app/catalog.json
COPY catalog.json /app/static/
COPY templates/ /app/templates/
COPY .env ./

# Install backend dependencies
RUN cd backend && uv pip install --system -e . && uv pip install --system bcrypt

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
