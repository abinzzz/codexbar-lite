PYTHON ?= python3
PREFIX ?= $(CURDIR)/.build/install

.PHONY: build test check
build:
	$(PYTHON) tools/install.py --prefix "$(PREFIX)"
test:
	$(PYTHON) -m unittest discover -s tests -v
check: build test
	"$(PREFIX)/bin/codexbar-lite" --version
	"$(PREFIX)/bin/codexbar-lite" menu --demo > /dev/null
