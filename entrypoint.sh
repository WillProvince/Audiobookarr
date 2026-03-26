#!/bin/sh
# Entrypoint: run as root, remap audiobookarr uid/gid to match the host user,
# chown the bind-mounted volumes, then drop privileges with gosu.
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Starting with PUID=${PUID} PGID=${PGID}"

groupmod -o -g "$PGID" audiobookarr
usermod -o -u "$PUID" audiobookarr

chown -R audiobookarr:audiobookarr /data /downloads /audiobooks

exec gosu audiobookarr "$@"
