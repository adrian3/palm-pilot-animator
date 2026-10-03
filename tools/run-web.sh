#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -n "${PALM_PYTHON:-}" ]; then
 python_cmd="$PALM_PYTHON"
elif [ -x "$project_dir/.venv/bin/python3" ]; then
 python_cmd="$project_dir/.venv/bin/python3"
else
 python_cmd=python3
fi
exec "$python_cmd" "$project_dir/tools/web-server.py" "$@"
