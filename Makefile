.PHONY: check eval test-unit test-acceptance verify-acceptance

check:
	cd service && uv run ruff format --check src tests
	cd service && uv run ruff check src tests
	cd service && uv run mypy src
	cd service && uv run pytest -q
	python scripts/acceptance_lock.py verify

test-unit:
	cd service && uv run pytest tests/unit -q

test-acceptance:
ifndef PHASE
	$(error Usage: make test-acceptance PHASE=N)
endif
	@test -d service/tests/acceptance/phase_$(PHASE) || (echo "No such phase directory: tests/acceptance/phase_$(PHASE)" && exit 1)
	cd service && uv run pytest tests/acceptance/phase_$(PHASE) -q -m acceptance || test $$? -eq 5

verify-acceptance:
	python scripts/acceptance_lock.py verify

eval:
	python evals/run.py
