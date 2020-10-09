.PHONY: default format white black lint test check clean pypireg pypi release

default: check

format: white
	isort setup.py pypoint/*.py

white: black

black:
	black . pypoint

lint: requirements.txt setup.py
	flake8
	pylint pypoint

check: format lint

clean:
	rm -f *.pyc
	rm -rf .tox
	rm -rf *.egg-info
	rm -rf __pycache__ pypoint/__pycache__
	rm -f pip-selfcheck.json
	rm -rf pytype_output

pypireg:
	python setup.py register -r pypi

pypi:
	rm -f dist/*.tar.gz
	python3 setup.py sdist
	twine upload dist/*.tar.gz

release:
	git diff-index --quiet HEAD -- && make check && bumpversion patch && git push --tags && git push && make pypi
