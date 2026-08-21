.PHONY: help install simulate train eval api demo test lint clean frontend all

PY ?= python3

help:
	@echo "AI Revenue Recovery — commands"
	@echo "  make install    Install Python dependencies"
	@echo "  make simulate   Generate synthetic subscription + failed-payment dataset"
	@echo "  make train      Train recovery-probability + optimal-timing models"
	@echo "  make eval       Run the engine vs baselines on the held-out set (writes reports/)"
	@echo "  make api        Run the FastAPI backend on :8000"
	@echo "  make demo       Recover one real Razorpay test-mode payment (needs keys)"
	@echo "  make test       Run the test suite"
	@echo "  make lint       Ruff lint"
	@echo "  make all        simulate + train + eval end-to-end"

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e .

simulate:
	$(PY) scripts/generate_data.py

train:
	$(PY) scripts/train_models.py

eval:
	$(PY) scripts/run_eval.py

api:
	$(PY) -m uvicorn recovery.api.app:app --reload --port 8000

demo:
	$(PY) scripts/demo_live.py

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests scripts

frontend:
	cd frontend && npm install && npm run dev

all: simulate train eval

clean:
	rm -rf data/*.parquet data/*.csv data/*.jsonl models/*.joblib reports/*.png reports/*.json
