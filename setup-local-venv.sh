#!/bin/bash

python3 -m venv venv_gymbot
source venv_gymbot/bin/activate && python -m pip install --upgrade pip && pip install -r requirements.txt && pip install -r requirements_local_venv.txt && pre-commit install