#!/bin/bash

# Start script for Linux
docker build -t prelegal .
docker run --rm --name prelegal-app -p 8000:8000 --env-file .env prelegal
