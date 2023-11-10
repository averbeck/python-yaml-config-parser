PYTHON ?= python3

APP_NAME := $(shell grep -oP '^name = \"\K[^ \"]+' pyproject.toml)
VERSION ?= $(shell git describe --tags --always --dirty)

BUILD_DIR := ./build
DIST_DIR := ./dist
SRC_DIR := ./$(subst -,_,$(APP_NAME))

VENV := ./venv
VENV_ACTIVATE := $(VENV)/bin/activate
VENV_DEV_MARKER := $(VENV)/development
VENV_MARKER := $(VENV)/base



SRC := $(shell find "$(SRC_DIR)" -type f -name '*.py')
WHEEL := $(DIST_DIR)/$(APP_NAME)-$(VERSION)-py3-none-any.whl

export SOURCE_DATE_EPOCH ?= $(shell git log --pretty='%ct' -n1 HEAD || echo 0)

default:

.PHONY: clean-pyc
clean-pyc:
	rm -rf __pycache__ */__pycache__  */*/__pycache__ */*/*/__pycache__

.PHONY: clean
clean: clean-pyc
	-deactivate
	rm -rf $(VENV)
	rm -fr reports/tests/*

.PHONY: clean-full
clean-full: clean
	rm -rf $(DIST_DIR)
	rm -rf .eggs *.egg-info */*.egg-info */*/*.egg-info

$(VENV_ACTIVATE):
	$(PYTHON) -m venv $(VENV)

.PHONY: venv
venv: $(VENV_MARKER)

$(VENV_MARKER): $(VENV_ACTIVATE)
#	-ssh -T git@ssh.dev.azure.com
	rm -f $(VENV_DEV_MARKER)
	. $(VENV_ACTIVATE) && $(PYTHON) -m pip install -e .
	touch $(VENV_MARKER)

.PHONY: venv-dev
venv-dev: $(VENV_DEV_MARKER)

$(VENV_DEV_MARKER): $(VENV_ACTIVATE) $(VENV_MARKER)
	. $(VENV_ACTIVATE) && $(PYTHON) -m pip install -e .[dev]
	touch $(VENV_DEV_MARKER)

requirements.txt: pyproject.toml
	. $(VENV)/bin/activate && $(PYTHON) -m pip freeze --exclude $(APP_NAME) > $(@)

.PHONY: wheel
wheel: $(WHEEL)

$(WHEEL): $(SRC)
	$(PYTHON) -m pip wheel -w $(DIST_DIR) .

.PHONY: debug
debug:
	echo "$(APP_NAME) v${VERSION}"
	echo "SRC_DIR: $(SRC_DIR)"

.PHONY: format
format: $(SRC)
	. $(VENV)/bin/activate && black $(SRC)

.PHONY: lint
lint: $(SRC)
	. $(VENV)/bin/activate && pylint $(SRC)

.PHONY: check
check: unittests

.PHONY: unittests
unittests: export PROJECT_DIR = $(shell pwd)
unittests: $(VENV_DEV_MARKER) $(SRC)
	mkdir -p docs/reports/tests
	rm -f /tmp/unittest.txt
	. $(VENV)/bin/activate && $(PYTHON) -m nose2 \
		--start-dir tests \
		--plugin nose2.plugins.junitxml \
		--junit-xml \
		--junit-xml-path reports/test_results.xml \
		--with-coverage \
		--coverage-config .coveragerc \
		--coverage-report xml \
		--coverage-report term