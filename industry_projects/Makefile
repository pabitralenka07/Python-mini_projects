# Unified Makefile for Python Intermediate Projects Portfolio
# Requires GNU Make and Python 3.12+ (tested on Python 3.14.3)

SHELL := /bin/bash
VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

.PHONY: help setup test test-cov lint format typecheck check clean seed-all \
        run-p01 run-p01-gui run-p02 run-p03 run-p04 run-p04-gui run-p05 \
        run-p06 run-p07 run-p08 run-p09 run-p09-gui run-p10 run-p11 run-p12 run-p13

help:
	@echo "======================================================================="
	@echo " Python Intermediate Projects Portfolio - Command Center"
	@echo "======================================================================="
	@echo "  make setup        - Create virtualenv and install dependencies"
	@echo "  make test         - Run full test suite (121 tests)"
	@echo "  make test-cov     - Run full test suite with code coverage report"
	@echo "  make lint         - Run ruff linter and format checks"
	@echo "  make format       - Auto-format code using ruff"
	@echo "  make typecheck    - Run mypy static type checking"
	@echo "  make check        - Run full quality gate (lint + typecheck + test)"
	@echo "  make seed-all     - Seed all database projects with realistic demo data"
	@echo "  make clean        - Remove caches and temporary test artifacts"
	@echo "-----------------------------------------------------------------------"
	@echo " Project Run Targets:"
	@echo "  make run-p01      - P01 Contact Management (CLI)"
	@echo "  make run-p01-gui  - P01 Contact Management (Tkinter GUI)"
	@echo "  make run-p02      - P02 Bank Management System"
	@echo "  make run-p03      - P03 ATM Management System"
	@echo "  make run-p04      - P04 Library Management (CLI)"
	@echo "  make run-p04-gui  - P04 Library Management (Tkinter GUI)"
	@echo "  make run-p05      - P05 Hospital Management System"
	@echo "  make run-p06      - P06 Bus Ticket Reservation System"
	@echo "  make run-p07      - P07 Airport Management System"
	@echo "  make run-p08      - P08 Zoo Management System"
	@echo "  make run-p09      - P09 Electricity Bill (CLI)"
	@echo "  make run-p09-gui  - P09 Electricity Bill (Tkinter GUI)"
	@echo "  make run-p10      - P10 Exam Seating Arrangement System"
	@echo "  make run-p11      - P11 Classic Snake Game (Pygame UI)"
	@echo "  make run-p12      - P12 Website Blocker (Dry-Run by Default)"
	@echo "  make run-p13      - P13 Parallel Image Downloader"
	@echo "======================================================================="

setup:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTEST) tests/ -v

test-cov:
	$(PYTEST) --cov=projects --cov=common tests/

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

typecheck:
	$(MYPY) common projects tests

check: lint typecheck test

seed-all:
	@echo "Seeding databases..."
	$(PYTHON) -m projects.p01_contact_management.seed
	$(PYTHON) -m projects.p02_bank_management.seed
	$(PYTHON) -m projects.p03_atm_management.seed
	$(PYTHON) -m projects.p04_library_management.seed
	$(PYTHON) -m projects.p05_hospital_management.seed
	$(PYTHON) -m projects.p06_bus_reservation.seed
	$(PYTHON) -m projects.p07_airport_management.seed
	$(PYTHON) -m projects.p08_zoo_management.seed
	$(PYTHON) -m projects.p09_electricity_bill.seed
	$(PYTHON) -m projects.p10_exam_seating.seed
	@echo "All databases seeded successfully!"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.part" -delete

# Project Runners
run-p01:
	$(PYTHON) -m projects.p01_contact_management

run-p01-gui:
	$(PYTHON) -m projects.p01_contact_management --gui

run-p02:
	$(PYTHON) -m projects.p02_bank_management

run-p03:
	$(PYTHON) -m projects.p03_atm_management

run-p04:
	$(PYTHON) -m projects.p04_library_management

run-p04-gui:
	$(PYTHON) -m projects.p04_library_management --gui

run-p05:
	$(PYTHON) -m projects.p05_hospital_management

run-p06:
	$(PYTHON) -m projects.p06_bus_reservation

run-p07:
	$(PYTHON) -m projects.p07_airport_management

run-p08:
	$(PYTHON) -m projects.p08_zoo_management

run-p09:
	$(PYTHON) -m projects.p09_electricity_bill

run-p09-gui:
	$(PYTHON) -m projects.p09_electricity_bill --gui

run-p10:
	$(PYTHON) -m projects.p10_exam_seating

run-p11:
	$(PYTHON) -m projects.p11_snake_game

run-p12:
	$(PYTHON) -m projects.p12_website_blocker

run-p13:
	$(PYTHON) -m projects.p13_image_downloader
