#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
while IFS= read -r node; do
    set -- "$@" --deselect "$node"
done < tests/beta93-only-tests.txt
exec python3 -m pytest -q "$@"
