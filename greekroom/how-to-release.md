# Release instructions

Using `uv`:  https://docs.astral.sh/uv/guides/package/

1. Update version like `uv version 1.1.0`
2. Clean previous builds like `rm -r dist/`
3. Build the project: `uv build`
4. Upload to **testpypi**:  `uv publish --publish-url https://test.pypi.org/legacy/ dist/* --token <YOUR_TESTPYPI_TOKEN>`
5. Upload to **pypi**:  `uv publish dist/* --token <YOUR_PYPI_TOKEN>`
