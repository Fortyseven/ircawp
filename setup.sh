#!/bin/bash

PATH_MODELS=models

set -e

function curl_model() {
    if [ -f "$PATH_MODELS/$2" ]; then
        echo "!! $PATH_MODELS/$2 already exists, skipping..."
        return
    fi

    echo "* Downloading $2..."
    curl $1 -o $PATH_MODELS/$2 -L
}

# check for venv, set it up if not present

# if [ ! -d "./venv" ]; then
#     echo "Creating virtual environment..."
#     python3 -m venv ./venv
#     source ./venv/bin/activate
#     pip install -r requirements.txt
# fi

# check for existing .env

if [ ! -f ".env" ]; then
    echo "Copying over sample .env file... fill this out with your Slack API keys!"
    cp scripts/example.env .env
fi

if [ ! -f "config.json" ]; then
    echo "Copying over default config.json..."
    cp scripts/config-example.json config.json
fi