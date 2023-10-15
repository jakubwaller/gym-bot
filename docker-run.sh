#!/usr/bin/env bash

docker stop gymbot
docker rm gymbot
docker run --restart always --name gymbot -d -v /home/ubuntu/gym-bot/logs/:/gymbot/logs gymbot/gymbot bash -c "cd /gymbot && python3 -m gymbot"
docker logs -f gymbot