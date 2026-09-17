.PHONY: test doctor install

VAULT ?= $(HOME)/Documents/ResearchVault

test:
	python3 -m unittest discover -s tests -v

doctor:
	python3 scripts/doctor.py --vault "$(VAULT)"

install:
	python3 scripts/bootstrap.py --vault "$(VAULT)" --install-skills --skill-mode symlink
