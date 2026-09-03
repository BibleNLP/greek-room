# Release instructions

Using `uv`:  https://docs.astral.sh/uv/guides/package/

1. Update version like `uv version 1.1.0`
2. Clean previous builds like `rm -r dist/`
3. Build the project: `uv build`
4. Upload to **testpypi**:  `uv publish --publish-url https://test.pypi.org/legacy/ dist/* --token <YOUR_TESTPYPI_TOKEN>`
5. Test install the new version in a new `test` directory:
   5.1 `uv venv .venv --python=3.12`
   5.2 `uv pip install --index https://test.pypi.org/simple/ \
    --index-strategy unsafe-best-match \
    greekroom==1.1.0`
6. Upload to **pypi**:  `uv publish dist/* --token <YOUR_PYPI_TOKEN>`
