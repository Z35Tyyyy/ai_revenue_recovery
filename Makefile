.PHONY: help install simulate train eval api demo test lint format format-check clean distclean frontend build-frontend serve all

PY ?= python3
PORT ?= 8000
HOST ?= 0.0.0.0

help:
	@echo "Rebound — commands"
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
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt
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
	$(PY) -m pytest --cov=recovery --cov-report=term-missing

lint:
	$(PY) -m ruff check src tests scripts

format:
	$(PY) -m ruff format src tests scripts

format-check:
	$(PY) -m ruff format --check src tests scripts

frontend:
	cd frontend && npm install && npm run dev

build-frontend:
	cd frontend && npm install && npm run build

# One process serves the built React app AND the API on $(PORT).
serve: build-frontend
	$(PY) -m uvicorn recovery.api.app:app --host $(HOST) --port $(PORT)

all: simulate train eval

# Remove only regenerable intermediates. Committed artifacts (models/*.joblib,
# reports/eval.json) are LEFT ALONE — use `make distclean` to wipe those too.
clean:
	rm -f data/population.json data/*.csv data/*.jsonl reports/*.png

distclean: clean
	rm -f models/*.joblib models/metrics.json reports/eval.json
