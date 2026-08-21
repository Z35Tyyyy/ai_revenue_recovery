.PHONY: help install simulate train eval api demo test lint clean frontend build-frontend serve all

PY ?= python3
PORT ?= 8000
HOST ?= 0.0.0.0

help:
	@echo "AI Revenue Recovery — commands"
	@echo "  make install         Install Python dependencies"
	@echo "  make simulate        Generate synthetic subscription + failed-payment dataset"
	@echo "  make train           Train recovery-probability + optimal-timing models"
	@echo "  make eval            Run the engine vs baselines on the held-out set (writes reports/)"
	@echo "  make api             Run the API in dev (reload) on :8000"
	@echo "  make frontend        Run the Vite dev server (hot reload) on :5173"
	@echo "  make build-frontend  Production-build the React app into frontend/dist"
	@echo "  make serve           Build the frontend + serve app + API on one port (production)"
	@echo "  make demo            Recover one real Razorpay test-mode payment (needs keys)"
	@echo "  make test            Run the test suite"
	@echo "  make lint            Ruff lint"
	@echo "  make all             simulate + train + eval end-to-end"

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
	$(PY) -m uvicorn recovery.api.app:app --reload --port $(PORT)

demo:
	$(PY) scripts/demo_live.py

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check src tests scripts

frontend:
	cd frontend && npm install && npm run dev

build-frontend:
	cd frontend && npm install && npm run build

# One process serves the built React app AND the API on $(PORT).
serve: build-frontend
	$(PY) -m uvicorn recovery.api.app:app --host $(HOST) --port $(PORT)

all: simulate train eval

clean:
	rm -rf data/*.parquet data/*.csv data/*.jsonl models/*.joblib reports/*.png reports/*.json
