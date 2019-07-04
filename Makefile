.PHONY: dev
dev: ## Run shell with source code and deps of scrapers inside Docker
	scripts/docker.sh build . --pull -t hyperschedule-scrapers:dev
	scripts/docker.sh run -it --rm -v "$${PWD}:/src" hyperschedule-scrapers:dev

.PHONY: help
help: ## Show this message
	@echo "usage:" >&2
	@grep -h "[#]# " $(MAKEFILE_LIST)	| \
		sed 's/^/  make /'		| \
		sed 's/:[^#]*[#]# /|/'		| \
		sed 's/%/LANG/'			| \
		column -t -s'|' >&2
