# Setup

1. Install Python >= 3.8
1. Clone the source code repository: `git clone https://github.com/IDEMSInternational/rapidpro-flow-toolkit`
1. Change to the project root directory: `cd rapidpro_flow_toolkit`
1. Create a virtual environment: `python -m venv .venv`
1. Activate venv: `source .venv/bin/activate`
1. Upgrade pip: `pip install --upgrade pip`
1. Install the project in dev mode: `pip install --editable .`

# Running tests

```sh
python -m unittest discover -s src
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


[1]: https://packaging.python.org/en/latest/guides/using-testpypi/
