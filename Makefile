ifndef version
	version = patch
endif

.PHONY: default format white black lint test check clean pypireg pypi release

default: check

check:
	pre-commit run --all

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
	git diff-index --quiet HEAD --
	make check
	bumpversion $(version)
	git push --tags
	git push
	make pypi
