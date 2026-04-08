# Start script for Windows
docker build -t prelegal .
docker run -p 8000:8000 --env-file .env prelegal