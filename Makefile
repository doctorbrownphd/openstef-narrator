.PHONY: install dev build serve test clean

install:                          ## Install package + API deps
	pip install -e ".[api,llm]"

dev:                              ## Run API + Vite dev server (two terminals)
	@echo "Terminal 1:  python -m openstef_narrator.api"
	@echo "Terminal 2:  cd web && npm run dev"
	@echo ""
	@echo "Or: make serve  (production mode, single process)"

build:                            ## Build frontend for production
	cd web && npm install && npm run build

serve: build                      ## Build + serve (single command)
	python -m openstef_narrator.api

test:                             ## Run all tests
	python -m pytest tests/ -q

clean:                            ## Remove build artifacts
	rm -rf web/dist web/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
