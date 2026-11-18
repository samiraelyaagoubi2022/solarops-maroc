export PYTHONPATH := src

.PHONY: test lint

test:
	pytest -q

lint:
	ruff check src tests