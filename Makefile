.PHONY: all build dist sdist wheel clean docs

PYTHON := python3

all: build

build: venv
	@source venv/bin/activate && python setup.py build

venv:
	$(PYTHON) -m venv venv
	venv/bin/pip install pipenv
	venv/bin/pip install $$(venv/bin/pipenv lock --requirements --dev)
	@echo "Created a Python virtual environment in venv"

dist: sdist wheel
	@echo "Distribution files are located in the dist directory"

sdist: venv
	@source venv/bin/activate && python setup.py sdist
	@echo "Python source distribution package has been created dist directory"

wheel: venv
	@source venv/bin/activate && python setup.py bdist_wheel
	@echo "Python Wheel built distribution package has been created dist directory"

docs: docs/build/html

docs/build/html: venv
	@source venv/bin/activate && cd docs && $(MAKE) html
	@echo "Html documentation has been generated in docs/build/html

test: venv
	@source venv/bin/activate && python setup.py test

test-mypy: build
	@echo "running MyPy"
	@source venv/bin/activate && mypy -p frames
	@echo "running MyPy completed"

clean:
	@$(PYTHON) setup.py clean -qa
	@cd docs && $(MAKE) clean

	@echo "removing '.tox'"
	@rm -rf .tox

	@echo "removing '.eggs'"
	@rm -rf .eggs

	@echo "removing 'Frames.egg-info'"
	@rm -rf frames.egg-info

	@echo "removing '.mypy_cache'"
	@rm -rf .mypy_cache

