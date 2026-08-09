PYTHON ?= python3

.PHONY: lint test

lint:
	@$(PYTHON) -m py_compile bump_semver.py tests/test_bump_semver.py

test:
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
