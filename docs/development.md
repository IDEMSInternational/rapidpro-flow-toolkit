# Setup

```sh
# Install Python >= 3.8
# Clone the source code repository
git clone https://github.com/IDEMSInternational/rapidpro-flow-toolkit

# Change to the project root directory
cd rapidpro_flow_toolkit

# Create a virtual environment
python -m venv .venv

# Activate venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install the project in dev mode
pip install --editable .
```

# Running tests

Run the whole test suite.
```sh
python -m unittest discover -s tests
```

Tests should be run after making any change to the code and certainly before creating a git commit.

# Pre-commit hooks

You may use [pre-commit] to run the following tools before every commit (in order):

- [black] - code formatter
- [flake8] - linter

Any violations found by either tool will abort the commit. Simply fix the issues found and try again.

To install pre-commit:
```
pip install pre-commit
```

# Build

1. Install the build tool: `pip install --upgrade build`
1. Build the project: `python -m build`
1. Results of the build should be found in the `dist` directory

To verify that the build produced a valid and working Python package, install the package in a clean virtual environment.

```sh
python -m venv build_verification
source build_verification/bin/activate
pip install dist/rpft-x.y.z-py3-none-any.whl
rpft --help
deactivate
rm -rf venv_verification
```

# Release

You will need:

- sufficient access to the Github repo to create Releases
- the project in a tested and fully-working state

Once ready:

1. Create a release in Github
1. Decide what the next version number should be
1. Edit the release notes
1. Publish the release

Upon publishing, the project should be tagged automatically with the release version number. This can be used later to build specific versions of the project.

# Upload to PyPI

## TestPyPI

It is recommended to get comfortable with uploading packages to PyPI by first experimenting on the test index. See [Using TestPyPI] for details.

## PyPI

You will need:

- an account on PyPI
- membership of the `rapidpro-flow-tools` project in PyPI
- the `twine` package installed

Once ready:

1. Check out the project at the relevant release tag
1. Build the project as per the [Build](#build) section
1. Upload to TestPyPI: `twine upload -r testpypi dist/*`
1. Check everything looks ok
1. Upload to PyPI: `twine upload dist/*`


[Using TestPyPI]: https://packaging.python.org/en/latest/guides/using-testpypi/
[pre-commit]: https://pre-commit.com/
[black]: https://black.readthedocs.io/en/stable/index.html
[flake8]: https://flake8.pycqa.org/en/latest/
