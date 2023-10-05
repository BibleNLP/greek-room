## Public Website
This directory houses the content, code and cofigurations for the public website of Greek Room.

### Technology Stack
- [Hugo](https://github.com/gohugoio/hugo)
- `Zen` [theme](https://github.com/frjo/hugo-theme-zen)

### Steps to Build on Porta
> Install all prequisites and packages from the links above.

```sh
# Add required tools on path
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:/opt/dart-sass/src/dart

cd /usr/local/src/greek-room/site

# Make sure your changes are present
# e.g. `git pull`, etc.

# Run hugo
hugo

# If successful, this will have created (or updated) the
# ./public direcory which contains the built site
```
