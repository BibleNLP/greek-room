## Public Website
This directory houses the content, code and cofigurations for the public website of Greek Room.

### Technology Stack
- [Hugo](https://github.com/gohugoio/hugo)
- `Zen` [theme](https://github.com/frjo/hugo-theme-zen)

### Steps to Build on Porta
> Note: Install all prequisites and packages from the links above.
> Also, some or all of these commands might require `sudo`. You could `sudo su` before running.

```sh
# Add required tools on path
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:/opt/dart-sass/src/dart

cd /usr/local/src/greek-room/site

# Make sure your changes are present
# e.g. `git pull`, etc.

# Run hugo
sudo hugo

# If successful, this will have created (or updated) the
# ./public direcory which contains the built site
```

### Run Development Server
To run a development server to view the website (this would not be reflected on the public website yet)
```sh
cd /usr/local/src/greek-room/site
hugo server --themesDir themes

# This would start a development server on port 1313 (by default).
# Ctrl+c to exit.
```

To view the website you can port-forward to your local machine. Run this on a new terminal on your local machine (e.g. laptop)
```sh
ssh -N -L 1313:localhost:1313 username@porta
```
Then go to localhost:1313 on your browser to view the website.

### Deploy to greekroom.org
To update the public version of the website (after testing using above steps):
> Note: Make sure you have built the site before attempting to do this. See [Steps to Build on Porta](#Steps-to-Build-on-Porta).
```sh
cd /usr/local/src/greek-room/site
cp -r public /usr/local/greek-room
# In this step we replace the existing
# `public` directory with the updated one

# Make the directory accessible by group
sudo chown -R :zion_users /usr/local/greek-room/public

# Change permissions
sudo chmod -R 775 /usr/local/greek-room/public
```

This should be enough to update the public website. Sometimes, `nginx` might need refreshing:
```sh
sudo nginx -s reload
```