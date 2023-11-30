## Ephesus
### Greek Room Web API and Reference App

### Docker Build
```
# From this directory.
# Assumes Docker is installed.

# Build image
docker build -t ephesus:2023.11.26.1 .

# Run container
docker run -d --name ephesus --mount source=ephesus-vol,target=/data -p 5000:80 --env-file .env ephesus:2023.11.26.1
```
