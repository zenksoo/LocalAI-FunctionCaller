RESET   = \033[0m

# text colors
BLACK   = \033[30m
GREEN   = \033[32m
RED     = \033[31m
YELLOW  = \033[33m
CYAN    = \033[36m
WHITE   = \033[37m

# background colors
BG_BLACK   = \033[40m
BG_RED     = \033[41m
BG_GREEN   = \033[42m
BG_YELLOW  = \033[43m
BG_CYAN    = \033[46m
BG_DEFAULT = \033[49m


# symbols
ARROW  = →
OK     = ✔
FAIL   = ✘

PYCACHE_FILES = $$(find . -type d -name "__pycache__")
MYPY_CACHES = $$(find . -type d -name ".mypy_cache")


install:
	@echo ""
	@echo "      $(BG_YELLOW)$(BLACK)   Install Dependencies ...   $(RESET)"
	@uv sync && \
			echo "\n$(BG_GREEN)$(BLACK)  All Dependencies Successfully Installed  $(RESET)" || \
			echo "\n$(BG_RED) $(RESET)  $(RED)$(FAIL) Installation Failed $(RESET)"

run:
	@uv run python3 -m src

debug:
	@uv run -m pdb -m src

# for web version
# checking if .venv already created then install flask and run the app
web:
	@if [ ! -d ".venv" ]; then \
		uv venv --clear;\
	fi
	@uv pip install flask flask_cors --python .venv
	@uv run python3 -m web

clean:
	@echo ""
	@echo "$(BG_YELLOW)$(BLACK)         CLEAN         $(RESET)"

	@sleep 0.3
	@rm -rf $(PYCACHE_FILES) && \
		echo "  $(GREEN)$(OK) pycache removed$(RESET)" || \
		(echo "  $(FAIL) nothing to remove$(RESET)"; exit 0)

	@sleep 0.3
	@rm -rf $(MYPY_CACHES) && \
		echo "  $(GREEN)$(OK) mypy_cache removed$(RESET)" || \
		(echo "  $(FAIL) nothing to remove$(RESET)"; exit 0)
	@echo ""
	@echo "$(BG_GREEN)$(BLACK)   $(OK) workspace is clean   $(RESET)"
	@echo ""

lint:
	@echo ""
	@echo "$(BG_GREEN)$(BLACK)    LINT CHECKS    $(RESET)"
	@echo ""

	@echo "$(BG_YELLOW)$(BLACK)  flake8  $(RESET)  $(YELLOW)$(ARROW) checking style...$(RESET)"
	@sleep 0.3
	@uv tool run flake8 . && \
			echo "$(BG_GREEN) $(RESET)  $(GREEN)$(OK) flake8 passed$(RESET)" || \
			(echo "$(BG_RED) $(RESET) $(RED)$(FAIL) flake8 failed$(RESET)"; exit 1)
	@echo ""

	@echo "$(BG_YELLOW)$(BLACK)  mypy    $(RESET)  $(YELLOW)$(ARROW) checking types...$(RESET)\n"
	@uv tool run mypy . --warn-return-any        \
	         --warn-unused-ignores   \
	         --ignore-missing-imports \
	         --disallow-untyped-defs \
	         --check-untyped-defs    \
	 && echo "$(BG_GREEN) $(RESET)  $(GREEN)$(OK) mypy passed$(RESET)" || \
	    (echo "\n$(BG_RED) $(RESET)  $(RED)$(FAIL) mypy failed$(RESET)"; exit 1)
	@echo ""

	@echo "$(BG_GREEN)$(BLACK)    $(OK) all checks passed    $(RESET)"
	@echo ""

.PHONY: web
