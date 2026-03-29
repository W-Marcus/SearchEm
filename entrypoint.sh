#!/bin/sh
# Solves permission issues with docker.
chown -R appuser /data /db
exec gosu appuser sh -c "python searchem_${SURFACE}.py \"$@\"" --  "$@"