#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PALM_SYNC_ROOT="$project_dir/.local/palm-sync"
case "${1:-backup}" in
 backup)
  export PALM_BACKUP=1
  backup_dir="$project_dir/backups/$(date +%Y%m%d-%H%M%S)"
  exec python3 "$project_dir/tools/palmconnect.py" "$backup_dir"
  ;;
 install)
  : "${2:?Supply the completed backup directory}"
  export PALM_BACKUP_DIR="$2"
  export PALM_INSTALL="$project_dir/build/PalmAnimation.prc"
  exec python3 "$project_dir/tools/palmconnect.py" "$project_dir/backups/install-$(date +%Y%m%d-%H%M%S)"
  ;;
 *) echo 'Usage: run-hotsync.sh backup | install BACKUP_DIRECTORY' >&2;exit 2;;
esac
