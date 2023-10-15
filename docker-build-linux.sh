#!/usr/bin/env bash

git pull
docker build -t gymbot/gymbot -f Dockerfile-linux .
