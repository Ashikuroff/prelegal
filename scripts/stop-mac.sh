#!/bin/bash

# Stop script for Mac
docker stop $(docker ps -q --filter ancestor=prelegal)
docker rm $(docker ps -a -q --filter ancestor=prelegal)