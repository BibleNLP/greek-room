# Release instructions

Using `uv`:  https://docs.astral.sh/uv/guides/package/

1. Update version like `uv version 1.1.0`
2. Clean previous builds like `rm -r dist/`
3. Upload to **testpypi**:  `uv publish --token <YOUR_TOKEN> --publish-url https://test.pypi.org/legacy/ dist/*`
