PY := .venv/bin/python
.PHONY: setup init-config auth-gmail doctor test lint
setup:
	python3.12 scripts/setup.py
init-config:
	$(PY) -m returnpath init-config
auth-gmail:
	$(PY) -m returnpath auth-gmail
doctor:
	$(PY) -m returnpath doctor $(SERVICE)
test:
	RP_ENV_FILE=/dev/null RP_MODE=local RP_ALLOW_CONNECTED_WRITES=false $(PY) -m pytest -q
lint:
	.venv/bin/ruff check src tests scripts

seed worker watchdog:
	RP_ENV_FILE=/dev/null RP_MODE=local $(PY) -m returnpath $@
