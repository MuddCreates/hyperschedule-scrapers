#!/bin/sh

set -e
set -o pipefail

cd /tmp
poetry install

rm /tmp/pyproject.toml /tmp/poetry.lock
rm /tmp/docker-install-project.sh
