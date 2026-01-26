# HomeSentry - Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed on MediaServer
- Git repository cloned to MediaServer
- Network access to services you want to monitor

## Installation Steps

### 1. Create Configuration File

```bash
# Navigate to project directory
cd ~/git/homesentry

# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

**Required changes in .env:**
- Set `DISCORD_WEBHOOK_URL` to your Discord webhook URL
- Verify `PLEX_URL`, `JELLYFIN_URL`, `PIHOLE_URL` match your setup
- Adjust thresholds if needed

### 2. Build and Start Container

```bash
# Build the Docker image
docker compose -f docker/docker-compose.yml build

# Start the container in detached mode
docker compose -f docker/docker-compose.yml up -d

# View logs to verify startup
docker compose -f docker/docker-compose.yml logs -f
```

### 3. Verify Installation

```bash
# Check container status (should show "healthy")
docker ps

# Test the health endpoint
curl http://localhost:8000/healthz

# Test the root endpoint
curl http://localhost:8000/
```

### 4. Access the Application

Open your browser and navigate to:
- **Dashboard:** http://192.168.1.8:8000
- **API Docs:** http://192.168.1.8:8000/docs
- **Health Check:** http://192.168.1.8:8000/healthz

## Useful Commands

### View Logs
```bash
docker compose -f docker/docker-compose.yml logs -f
```

### Restart Container
```bash
docker compose -f docker/docker-compose.yml restart
```

### Stop Container
```bash
docker compose -f docker/docker-compose.yml down
```

### Rebuild After Code Changes
```bash
docker compose -f docker/docker-compose.yml up --build -d
```

### Access Container Shell
```bash
docker exec -it homesentry /bin/bash
```

## Troubleshooting

### Container won't start
1. Check logs: `docker compose -f docker/docker-compose.yml logs`
2. Verify `.env` file exists and has correct values
3. Ensure port 8000 is not already in use: `netstat -tulpn | grep 8000`

### Health check failing
1. Check if application is running: `docker exec homesentry ps aux`
2. Test health endpoint from inside container: `docker exec homesentry curl localhost:8000/healthz`
3. Check application logs for errors

### Database issues
1. Ensure `data/` directory exists and has proper permissions
2. Check if database file is created: `ls -la data/`
3. Verify volume mount in docker-compose.yml

## Next Steps

After verifying the skeleton works:
1. Complete the database schema feature
2. Implement system collector
3. Add service health checks
4. Set up Discord alerts
5. Build the HTML dashboard

## File Structure

```
homesentry/
├── app/
│   ├── main.py              # FastAPI application ✓
│   ├── collectors/          # Monitoring modules (future)
│   ├── storage/             # Database modules (future)
│   ├── alerts/              # Alert modules (future)
│   ├── templates/           # HTML templates (future)
│   └── static/              # CSS/JS files (future)
├── docker/
│   ├── Dockerfile           # Container build ✓
│   └── docker-compose.yml   # Deployment config ✓
├── data/                    # SQLite database (runtime)
├── .env                     # Configuration (you create this)
├── .env.example            # Configuration template ✓
└── requirements.txt        # Python dependencies ✓
```

## Notes

- The application is currently just a skeleton - collectors and dashboard will be added in future features
- Database schema will be created in the next feature
- Discord alerts require webhook configuration
- All configuration is via environment variables (never hardcode)
