#!/bin/sh
set -eu

# Claude sends hook context as JSON on stdin. It must be consumed before exit.
cat >/dev/null
printf '%s\n' '{"terminalSequence":"\u0007"}'
