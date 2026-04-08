#!/bin/bash

# Stop script for Linux
docker stop $(docker ps -q --filter ancestor=prelegal)
docker rm $(docker ps -a -q --filter ancestor=prelegal)