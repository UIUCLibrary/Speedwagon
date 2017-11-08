.PHONY: clean docs build
PYTHON := python3
build: venv
	@source venv/bin/activate && python setup.py sdist

wheel: venv
	@source venv/bin/activate && python setup.py bdist_wheel

venv:
	$(PYTHON) -m venv venv
	@source venv/bin/activate && pip install -r requirements-dev.txt

clean:
	@$(PYTHON) setup.py clean
	@cd docs && $(MAKE) clean

	@echo "removing '.tox'"
	@rm -rf .tox

	@echo "removing '.eggs'"
	@rm -rf .eggs

	@echo "removing 'frames.egg-info'"
	@rm -rf frames.egg-info


docs: venv
	@echo building docs
	@source venv/bin/activate && cd docs && $(MAKE) html
