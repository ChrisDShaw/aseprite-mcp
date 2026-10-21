#!/bin/sh
# Run Aseprite from the aseprite-from-source Docker image.
# Mounts temp dirs and $HOME at identical paths so host file paths
# used by aseprite-mcp resolve inside the container.
exec docker run --rm \
  -v /tmp:/tmp \
  -v /private/tmp:/private/tmp \
  -v /var/folders:/var/folders \
  -v "$HOME:$HOME" \
  -w "$PWD" \
  aseprite-from-source:latest "$@"
