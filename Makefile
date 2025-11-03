.PHONY: help install run run-backend run-frontend run-all stop clean test

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Run both frontend and backend"
	@echo "  make run-backend   - Run only the backend API"
	@echo "  make run-frontend  - Run only the frontend Streamlit app"
	@echo "  make stop          - Stop all running processes"
	@echo "  make clean         - Clean up temporary files"
	@echo "  make test          - Run tests (if available)"

# Install dependencies
install:
	@echo "Installing dependencies..."
	uv sync || pip install -r requirements.txt

# Run backend API
run-backend:
	@echo "Starting FastAPI backend on http://localhost:8000"
	@uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run frontend Streamlit app
run-frontend:
	@echo "Starting Streamlit frontend on http://localhost:8501"
	@uv run streamlit run frontend/app.py --server.headless true

# Run both frontend and backend in parallel
run-all:
	@echo "Starting both backend and frontend..."
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend UI: http://localhost:8501"
	@echo "Press Ctrl+C to stop both servers"
	@bash -c 'trap "kill 0" EXIT; \
	uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload & \
	uv run streamlit run frontend/app.py --server.headless true & \
	wait'

# Alias for run-all
run: run-all

# Stop all processes (finds and kills uvicorn and streamlit processes)
stop:
	@echo "Stopping all processes..."
	@pkill -f "uvicorn backend.api.main" || true
	@pkill -f "streamlit run frontend/app.py" || true
	@pkill -f "uv run uvicorn" || true
	@pkill -f "uv run streamlit" || true
	@echo "All processes stopped"

# Clean temporary files
clean:
	@echo "Cleaning up temporary files..."
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.log" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	@echo "Cleanup complete"

# Run tests (placeholder - add your test commands here)
test:
	@echo "Running tests..."
	@echo "No tests configured yet"

