# Makefile for FAT Recovery Tool
# Sử dụng: make <target>

# Variables
PYTHON = python
MAIN_SCRIPT = fat_recovery_modular.py
DEMO_SCRIPT = demo_modular.py
TEST_SCRIPT = test_modules.py

# Default target
.PHONY: help
help:
	@echo "FAT Recovery Tool - Available commands:"
	@echo ""
	@echo "  make demo     - Chạy demo các module"
	@echo "  make test     - Chạy unit tests"
	@echo "  make clean    - Dọn dẹp files tạm"
	@echo "  make help     - Hiển thị help này"
	@echo "  make run E    - Chạy phân tích ổ E: (ví dụ)"
	@echo ""
	@echo "Sử dụng trực tiếp:"
	@echo "  python $(MAIN_SCRIPT) <drive> [--recovery] [--info-only]"

# Run demo
.PHONY: demo
demo:
	@echo "Chạy demo các module..."
	$(PYTHON) $(DEMO_SCRIPT)

# Run tests
.PHONY: test
test:
	@echo "Chạy unit tests..."
	$(PYTHON) $(TEST_SCRIPT)

# Clean temporary files
.PHONY: clean
clean:
	@echo "Dọn dẹp files tạm..."
	-del /q __pycache__\*.pyc 2>nul
	-rmdir /s /q __pycache__ 2>nul
	-del /q *.tmp 2>nul
	-del /q *_backup.bin 2>nul
	@echo "Đã dọn dẹp xong!"

# Run analysis (example: make run E)
.PHONY: run
run:
	@if "$(filter-out $@,$(MAKECMDGOALS))" == "" ( \
		echo "Cần chỉ định ổ đĩa. Ví dụ: make run E" \
	) else ( \
		echo "Chạy phân tích ổ đĩa $(filter-out $@,$(MAKECMDGOALS))..." && \
		$(PYTHON) $(MAIN_SCRIPT) $(filter-out $@,$(MAKECMDGOALS)) \
	)

# Prevent make from treating drive letters as targets
%:
	@:
