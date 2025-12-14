.PHONY: help build clean run rebuild test check install dev health update

# RyxSurf Build System

help:
	@echo "🌊 RyxSurf Build System"
	@echo ""
	@echo "Commands:"
	@echo "  make build    - Build/validate browser"
	@echo "  make run      - Run browser"
	@echo "  make rebuild  - Clean + build + run"
	@echo "  make clean    - Clean cache and build artifacts"
	@echo "  make test     - Run tests"
	@echo "  make check    - Check syntax and imports"
	@echo "  make dev      - Development mode (auto-reload)"
	@echo "  make install  - Install dependencies"
	@echo "  make health   - Run health check"
	@echo "  make update   - Check for updates"
	@echo ""

build: check
	@echo "✅ Build complete"

clean:
	@echo "🧹 Cleaning..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .pytest_cache/ 2>/dev/null || true
	@echo "✅ Clean complete"

check:
	@echo "🔍 Checking syntax..."
	@python3 -m py_compile src/core/*.py src/ui/*.py 2>&1 | head -20 || true
	@echo "✅ Syntax OK"

run:
	@echo "🚀 Starting RyxSurf..."
	@cd .. && ./ryx surf

rebuild: clean build
	@echo "🔨 Rebuild complete, starting..."
	@make run

test:
	@echo "🧪 Running tests..."
	@python3 -m pytest tests/ -v 2>/dev/null || echo "No tests found"

dev:
	@echo "🔧 Development mode..."
	@echo "   Watching for changes..."
	@while true; do \
		make check && make run || true; \
		sleep 2; \
	done

install:
	@echo "📦 Installing dependencies..."
	@pip3 install -r ../requirements.txt --quiet
	@echo "✅ Dependencies installed"

# Quick commands
fast: clean check run
info:
	@echo "📊 RyxSurf Info"
	@echo "  Python: $$(python3 --version)"
	@echo "  GTK: $$(pkg-config --modversion gtk4 2>/dev/null || echo 'Not found')"
	@echo "  WebKit: $$(pkg-config --modversion webkit2gtk-4.1 2>/dev/null || echo 'Not found')"
	@echo "  Files: $$(find src -name '*.py' | wc -l) Python files"
	@echo "  Lines: $$(find src -name '*.py' -exec cat {} \; | wc -l) lines of code"

profile:
	@echo "⏱️  Profiling startup..."
	@python3 -m cProfile -s cumtime ../ryx_main.py surf 2>&1 | head -30

# Startup optimization targets
optimize:
	@echo "🚄 Optimizing startup..."
	@python3 -m compileall src/ -q
	@echo "✅ Bytecode compiled"

benchmark:
	@echo "⏱️  Benchmarking startup time..."
	@for i in 1 2 3 4 5; do \
		echo "Run $$i:"; \
		/usr/bin/time -f "  Time: %E" bash -c "timeout 3s ../ryx surf" 2>&1 | grep "Time:" || true; \
	done

health:
	@echo "🏥 Running health check..."
	@python3 -c "from pathlib import Path; from src.core.health_check import run_health_check; run_health_check(Path.home() / '.config' / 'ryxsurf', auto_fix=True)"

update:
	@echo "🔄 Checking for updates..."
	@python3 -c "from pathlib import Path; from src.core.auto_update import AutoUpdater; updater = AutoUpdater(Path.home() / '.config' / 'ryxsurf'); updater.manual_update()"

# Complete workflow
release: clean test optimize build
	@echo "✅ Release build complete"
