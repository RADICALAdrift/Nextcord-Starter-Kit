#!/usr/bin/env bash
set -e

cd "$(dirname "$0")" || exit 1

if [[ ! -d ".venv" ]]; then
    python3.12 -m venv .venv
fi

source .venv/bin/activate

python -m pip install -U pip

python -m pip install -r requirements.txt

python bot.py