# Idea Archive - Homelab Setup

## Prerequisites
- Docker and Docker Compose installed
- Port 3000 available

## Installation

1. Clone or create the directory structure:
```bash
mkdir -p idea-archive/public
cd idea-archive
```

2. Create all the files as shown above:
   - docker-compose.yml
   - Dockerfile
   - package.json
   - server.js
   - init.sql
   - public/index.html

3. Start the services:
```bash
docker-compose up -d
```

4. Check logs:
```bash
docker-compose logs -f
```

5. Access the archive:
   - Browse: http://your-homelab-ip:3000
   - API: http://your-homelab-ip:3000/api/ideas

## Usage

### From the Artifact
1. Set your homelab URL in the artifact (e.g., `http://192.168.1.100:3000`)
2. Generate an idea elaboration
3. Click "Save to Archive"

### Browse Your Ideas
Visit http://your-homelab-ip:3000 to:
- View all saved ideas
- Search your archive
- Click any idea to see full details

## Database Access

Connect directly to PostgreSQL:
```bash
docker exec -it idea-archive-db psql -U ideauser -d idea_archive
```

## Backup

Backup your ideas:
```bash
docker exec idea-archive-db pg_dump -U ideauser idea_archive > backup.sql
```

Restore:
```bash
docker exec -i idea-archive-db psql -U ideauser idea_archive < backup.sql
```
