export PYTHONPATH := src

.PHONY: test eval demo audit lint
test:
	python -m unittest discover -s . -p "test_*.py" -t .
eval:
	python -m kabyle_agents eval
demo:
	python -m kabyle_agents ask "un dictionnaire kabyle de la médecine" --trace
audit:
	python -m kabyle_agents audit
lint:
	ruff check .
