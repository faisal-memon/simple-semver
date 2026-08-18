PYTHON ?= python3

.PHONY: lint test

lint:
	@$(PYTHON) -m py_compile bump_semver.py config.py git_ops.py github_labels.py semver.py tests/test_bump_semver.py

test:
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
