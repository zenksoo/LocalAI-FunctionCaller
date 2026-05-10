BOLD    = \033[1m
RESET   = \033[0m

# text colors
BLACK   = \033[30m
GREEN   = \033[32m
YELLOW  = \033[33m
CYAN    = \033[36m
WHITE   = \033[37m

# background colors
BG_BLACK   = \033[40m
BG_GREEN   = \033[42m
BG_YELLOW  = \033[43m
BG_CYAN    = \033[46m
BG_DEFAULT = \033[49m

# symbols
ARROW  = →
OK     = ✔
FAIL   = ✘
SEP    = ════════════════════════════════

PYCACHE_FILES = $$(find . -type d -name "__pycache__")
MYPY_CACHES = $$(find . -type d -name ".mypy_cache")


install:
	@uv sync

run:
	@uv run python3 -m src

debug:
	@uv run -m pdb -m src.main

clean:
	@echo ""
	@echo "$(BOLD)$(CYAN)$(SEP)$(RESET)"
	@echo "$(BOLD)$(CYAN)  🧹 CLEAN$(RESET)"
	@echo "$(BOLD)$(CYAN)$(SEP)$(RESET)"
	@echo ""

	@sleep 0.3
	@rm -rf $(PYCACHE_FILES) && echo "  $(GREEN)$(OK) pycache removed$(RESET)" || (echo "  $(FAIL) nothing to remove$(RESET)"; exit 0)

	@sleep 0.3
	@rm -rf $(MYPY_CACHES) && echo "  $(GREEN)$(OK) mypy_cache removed$(RESET)" || (echo "  $(FAIL) nothing to remove$(RESET)"; exit 0)
	@echo ""

	@echo "$(BOLD)$(GREEN)$(SEP)$(RESET)"
	@echo "$(BOLD)$(GREEN)  $(OK) workspace is clean$(RESET)"
	@echo "$(BOLD)$(GREEN)$(SEP)$(RESET)"
	@echo ""

lint:
	@echo ""
	@echo "$(BOLD)$(CYAN)$(SEP)$(RESET)"
	@echo "$(BOLD)$(CYAN)  🔍 LINT CHECKS$(RESET)"
	@echo "$(BOLD)$(CYAN)$(SEP)$(RESET)"
	@echo ""

	@echo "$(BG_YELLOW)$(BLACK)$(BOLD)  flake8  $(RESET)  $(YELLOW)$(ARROW) checking style...$(RESET)"
	@sleep 0.3
	@uv tool run flake8 src && echo "  $(GREEN)$(OK) flake8 passed$(RESET)" || (echo "  $(FAIL) flake8 failed$(RESET)"; exit 1)
	@echo ""

	@echo "$(BG_CYAN)$(BLACK)$(BOLD)  mypy    $(RESET)  $(CYAN)$(ARROW) checking types...$(RESET)"
	@uv tool run mypy . --warn-return-any        \
	         --warn-unused-ignores   \
	         --ignore-missing-imports \
	         --disallow-untyped-defs \
	         --check-untyped-defs    \
	 && echo "  $(GREEN)$(OK) mypy passed$(RESET)" || (echo "  $(FAIL) mypy failed$(RESET)"; exit 1)
	@echo ""

	@echo "$(BOLD)$(GREEN)$(SEP)$(RESET)"
	@echo "$(BOLD)$(GREEN)  $(OK) all checks passed$(RESET)"
	@echo "$(BOLD)$(GREEN)$(SEP)$(RESET)"
	@echo ""

