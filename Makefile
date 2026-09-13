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

seed:
	RP_MODE=local RP_ALLOW_CONNECTED_WRITES=false $(PY) -m returnpath $@

worker watchdog web dev connected-seed connected-dev connected-smoke:
	$(PY) -m returnpath $@

eval:
	RP_ENV_FILE=/dev/null RP_MODE=local RP_ALLOW_CONNECTED_WRITES=false $(PY) scripts/evaluate.py
review-check: lint test
	RP_ENV_FILE=/dev/null $(PY) -m returnpath review-check
submission-check:
	RP_ENV_FILE=/dev/null $(PY) -m returnpath submission-check

demo:
	RP_ENV_FILE=/dev/null RP_MODE=local RP_ALLOW_CONNECTED_WRITES=false $(PY) scripts/demo.py

stripe-oracle:
	$(PY) -m returnpath stripe-oracle

live-model-eval:
	$(PY) scripts/model_eval.py
evidence-export:
	$(PY) scripts/export_evidence.py
voice-smoke:
	@echo "BLOCKED: optional voice deferred until connected core gates pass"
	@exit 1
