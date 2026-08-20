PYTHON ?= python3

.PHONY: lint test

lint:
	@$(PYTHON) -m py_compile main.py config.py git_ops.py pr_labels.py errors.py semver.py tests/test_config.py tests/test_pr_labels.py tests/test_semver.py

test:
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
