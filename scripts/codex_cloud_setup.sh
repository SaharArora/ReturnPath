#!/usr/bin/env bash
# Credential-free cloud setup. Safe for the initial specification-only repo.
set -euo pipefail
printf 'Runtime: '
python3 --version
if [[ -f Makefile ]] && grep -Eq '^setup[[:space:]]*:' Makefile; then
  # This target must install locked local dependencies only, never seed providers.
  make setup
else
  printf '%s\n' 'Specification-only checkout: no application setup target yet.'
  printf '%s\n' 'Codex should implement Makefile/setup first; no tests have run here.'
fi
