# NavSwap Deployment Guide - AWS EC2

## Prerequisites

- AWS Account
- EC2 instance (Ubuntu 22.04 LTS)
- Minimum: t3.medium (2 vCPU, 4GB RAM)
- Recommended: t3.large (2 vCPU, 8GB RAM)
- Docker and Docker Compose installed
- Domain name (optional)

---

## Step 1: Launch EC2 Instance

### 1.1 Create Instance

```bash
# Instance specifications:
- AMI: Ubuntu Server 22.04 LTS
- Instance Type: t3.large
- Storage: 30GB gp3
- Security Group: Allow ports 22, 80, 443, 8000
```

### 1.2 Configure Security Group

```bash
# Inbound Rules:
Type            Protocol    Port Range    Source
SSH             TCP         22            Your IP
HTTP            TCP         80            0.0.0.0/0
HTTPS           TCP         443           0.0.0.0/0
Custom TCP      TCP         8000          0.0.0.0/0 (or specific IPs)
```

---

## Step 2: Connect and Setup

### 2.1 SSH into Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

### 2.2 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.3 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

### 2.4 Install Git

```bash
sudo apt install git -y
```

---

## Step 3: Deploy Application

### 3.1 Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/your-org/navswap-backend.git
cd navswap-backend
```

### 3.2 Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Edit these variables:**

```bash
# Change JWT secret
JWT_SECRET_KEY=your-production-secret-key-here

# Update hosts for production
API_HOST=0.0.0.0
API_PORT=8000

# Add AWS credentials (if using AWS services)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Production settings
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
```

### 3.3 Place ML Models

```bash
# Upload your model files to /models/ directory
# Using SCP from your local machine:

# From your local machine:
scp -i your-key.pem models/*.pkl ubuntu@your-ec2-ip:/home/ubuntu/navswap-backend/models/
```

---

## Step 4: Start Services

### 4.1 Build and Start

```bash
# Build containers
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4.2 Verify Services

```bash
# Check if all containers are running
docker-compose ps

# Check logs
docker-compose logs -f backend

# Test health endpoint
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T12:00:00Z",
  "models_loaded": "13/13",
  "database": "connected"
}
```

---

## Step 5: Seed Database

```bash
# Run seed script
docker-compose exec backend python scripts/seed_data.py
```

---

## Step 6: Configure Nginx (Recommended)

### 6.1 Install Nginx

```bash
sudo apt install nginx -y
```

### 6.2 Configure Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/navswap
```

**Add this configuration:**

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use EC2 public IP

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.3 Enable and Restart

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/navswap /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## Step 7: Setup SSL (Optional but Recommended)

### 7.1 Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 7.2 Obtain Certificate

```bash
sudo certbot --nginx -d your-domain.com
```

Follow prompts to configure SSL.

---

## Step 8: Configure Monitoring

### 8.1 Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/navswap
```

**Add:**

```bash
/var/log/navswap/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
```

### 8.2 Setup CloudWatch (Optional)

Install CloudWatch agent for monitoring:

```bash
# Download agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb

# Install
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure (follow AWS documentation)
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

---

## Step 9: Backup Strategy

### 9.1 MongoDB Backup

```bash
# Create backup script
nano /home/ubuntu/backup-mongo.sh
```

**Script content:**

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker-compose exec -T mongo mongodump --archive > $BACKUP_DIR/navswap_$TIMESTAMP.archive

# Keep only last 7 days
find $BACKUP_DIR -name "navswap_*.archive" -mtime +7 -delete
```

```bash
chmod +x /home/ubuntu/backup-mongo.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/ubuntu/backup-mongo.sh
```

---

## Step 10: Maintenance Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart backend only
docker-compose restart backend
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Database Operations

```bash
# Access MongoDB shell
docker-compose exec mongo mongosh navswap

# Import data
docker-compose exec -T mongo mongorestore --archive < backup.archive

# Check database size
docker-compose exec mongo mongosh --eval "db.stats()"
```

---

## Step 11: Performance Optimization

### 11.1 Tune MongoDB

Edit `docker-compose.yml`:

```yaml
mongo:
  command: mongod --wiredTigerCacheSizeGB 2
```

### 11.2 Tune Nginx

```bash
sudo nano /etc/nginx/nginx.conf
```

**Optimize:**

```nginx
worker_processes auto;
worker_connections 2048;

# Enable gzip
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_types text/plain application/json;
```

---

## Step 12: Security Hardening

### 12.1 Configure Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 12.2 Disable Root Login

```bash
sudo nano /etc/ssh/sshd_config

# Set:
PermitRootLogin no
PasswordAuthentication no

sudo systemctl restart sshd
```

### 12.3 Setup Fail2Ban

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. MongoDB not ready -> Wait 30 seconds and restart
# 2. Port already in use -> Change port in docker-compose.yml
# 3. Models not found -> Check /models/ directory
```

### High Memory Usage

```bash
# Check memory
free -h

# Restart services
docker-compose restart

# Prune Docker
docker system prune -a
```

### Database Connection Issues

```bash
# Test MongoDB connection
docker-compose exec backend python -c "from app.database import connect_to_mongodb; import asyncio; asyncio.run(connect_to_mongodb())"
```

---

## Monitoring Endpoints

- Health: `http://your-domain.com/health`
- API Docs: `http://your-domain.com/docs`
- Metrics: `http://your-domain.com/metrics` (if Prometheus enabled)

---

## Production Checklist

- [ ] SSL certificate installed
- [ ] Environment variables secured
- [ ] JWT secret changed
- [ ] Firewall configured
- [ ] Backups automated
- [ ] Monitoring setup
- [ ] Log rotation configured
- [ ] Nginx reverse proxy enabled
- [ ] ML models uploaded
- [ ] Database seeded
- [ ] Health check passing

---

## Cost Estimation (AWS)

- **t3.large EC2**: ~$60/month
- **30GB EBS**: ~$3/month
- **Data Transfer**: ~$10/month (varies)
- **Total**: ~$75/month

For production at scale, consider:
- Load balancer
- Auto-scaling group
- RDS for MongoDB (managed)
- ElastiCache for Redis

---

## Support

For deployment issues: `ops@navswap.com`
