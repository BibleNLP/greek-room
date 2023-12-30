## Ephesus
### Greek Room Web API and Reference Application

### Docker Compose
```sh
# Assumes Docker Compose is installed.

# Go to the docker-compose directory
cd docker-compose

# Setup environment variables in the *.env files
# Start docker compose
docker compose up -d
```

### Backups
There are two levels of backups setup:
- Volume: The whole volume is snapshot and kept on disk (see `docker-compose.yml` for location details). This is setup automatically via `docker-compose`.
- DB: The DB is dumped periodically and kept on disk (details can be found in `cron` directory). This needs to be setup manually by:
`crontab -i cron/crontab`

#### Restore From Backup
To restore the docker volume snapshots (based on [offen](https://offen.github.io/docker-volume-backup/how-tos/restore-volumes-from-backup.html)):
```sh
# Trigger a manual backup before deleting volumes. Here the name of the container running offen is assumed to be `backup`.
docker exec backup backup

# Stop the containers
docker compose down

# Delete the existing volumes
docker volume rm greek-room_ephesus-data greek-room_postgres-data

# Restore the specific snapshot from local disk (e.g. backup-2023-12-27T04-00-00.tar.gz)
docker run --rm -it -v greek-room_ephesus-data:/backup/ephesus_database -v greek-room_postgres-data:/backup/postgres_database -v /usr/local/backups/docker\
-volumes:/archive:ro alpine tar -xvzf /archive/backup-2023-12-27T04-00-00.tar.gz
```