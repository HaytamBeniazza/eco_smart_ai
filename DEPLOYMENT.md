# EcoSmart AI - Deployment Guide 🚀

## 📋 Overview

This guide covers deploying the EcoSmart AI Multi-Agent Energy Management System using Docker containers for production environments.

## 🛠️ Prerequisites

- **Docker** (version 20.0 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Git** (for cloning the repository)
- **Minimum 4GB RAM** for optimal performance
- **2 CPU cores** recommended

## 🚀 Quick Start (Development)

```bash
# Clone the repository
git clone https://github.com/HaytamBeniazza/eco_smart_ai.git
cd eco_smart_ai

# Start services with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 🏗️ Production Deployment

### 1. Environment Configuration

Create `.env` file for production settings:

```bash
# .env
NODE_ENV=production
PYTHONPATH=/app
ENV=production

# Database settings (if using external DB)
DATABASE_URL=postgresql://user:password@db:5432/ecosmart

# Security settings
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Monitoring
SENTRY_DSN=your-sentry-dsn
LOG_LEVEL=INFO
```

### 2. Production Docker Compose

For production with nginx reverse proxy:

```bash
# Start with production profile
docker-compose --profile production up -d

# Or use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### 3. SSL/HTTPS Setup

```bash
# Create SSL certificates directory
mkdir ssl

# Generate self-signed certificates (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem

# For production, use Let's Encrypt:
# docker run -it --rm \
#   -v /path/to/ssl:/etc/letsencrypt \
#   certbot/certbot certonly --standalone \
#   -d your-domain.com
```

## 🔧 Configuration Options

### Backend Configuration

Environment variables for backend service:

```bash
# Performance
UVICORN_WORKERS=4
UVICORN_PORT=8000
UVICORN_HOST=0.0.0.0

# Agent settings
AGENT_POLLING_INTERVAL=30
WEATHER_API_INTERVAL=900
OPTIMIZATION_INTERVAL=300

# Morocco-specific settings
TIMEZONE=Africa/Casablanca
CURRENCY=DH
UTILITY_COMPANY=ONEE
```

### Frontend Configuration

Environment variables for frontend service:

```bash
# API endpoints
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Features
VITE_ENABLE_SCENARIOS=true
VITE_ENABLE_ANALYTICS=true
VITE_DEMO_MODE=false
```

## 📊 Monitoring & Health Checks

### Health Check Endpoints

- **Frontend**: `http://localhost:3000/`
- **Backend**: `http://localhost:8000/`
- **Nginx**: `http://localhost/health`

### Service Status

```bash
# Check all services
docker-compose ps

# View resource usage
docker stats

# Check logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs nginx
```

### Application Monitoring

```bash
# Backend metrics
curl http://localhost:8000/api/agents/status

# System health
curl http://localhost:8000/api/energy/current

# Demo scenarios status
curl http://localhost:8000/api/scenarios/results
```

## 🔒 Security Considerations

### 1. Network Security

```bash
# Create secure network
docker network create --driver bridge ecosmart-secure

# Use internal network for services
# (Configure in docker-compose.yml)
```

### 2. Container Security

```bash
# Run containers as non-root user
# (Already configured in Dockerfiles)

# Limit container resources
# Add to docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

### 3. Data Protection

```bash
# Backup volumes
docker run --rm -v ecosmart_backend-data:/data \
  -v $(pwd)/backups:/backup alpine \
  tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore from backup
docker run --rm -v ecosmart_backend-data:/data \
  -v $(pwd)/backups:/backup alpine \
  tar xzf /backup/data-backup-YYYYMMDD.tar.gz -C /data
```

## 🧪 Testing Deployment

### 1. Smoke Tests

```bash
# Test API endpoints
curl -f http://localhost:8000/ || echo "Backend failed"
curl -f http://localhost:3000/ || echo "Frontend failed"

# Test WebSocket connection
curl -f http://localhost:8000/ws || echo "WebSocket failed"

# Test demo scenarios
curl -X POST http://localhost:8000/api/scenarios/run/morning_optimization
```

### 2. Load Testing

```bash
# Install artillery for load testing
npm install -g artillery

# Create load test config
cat > artillery-config.yml << EOF
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - flow:
    - get:
        url: "/api/energy/current"
    - get:
        url: "/api/weather/current"
    - get:
        url: "/api/agents/status"
EOF

# Run load test
artillery run artillery-config.yml
```

## 🔄 Updates & Maintenance

### 1. Rolling Updates

```bash
# Update backend only
docker-compose up -d --no-deps backend

# Update frontend only  
docker-compose up -d --no-deps frontend

# Update all services
docker-compose pull
docker-compose up -d
```

### 2. Database Migrations

```bash
# If using database migrations
docker-compose exec backend python migrate.py

# Backup before migrations
docker-compose exec backend python backup_db.py
```

### 3. Log Rotation

```bash
# Configure log rotation in docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Change ports in docker-compose.yml
   ports:
     - "8001:8000"  # Use different external port
   ```

2. **Memory issues**
   ```bash
   # Check container memory usage
   docker stats --no-stream
   
   # Increase memory limits
   # Add to docker-compose.yml under services
   mem_limit: 1g
   ```

3. **Network connectivity**
   ```bash
   # Test inter-service communication
   docker-compose exec frontend ping backend
   docker-compose exec backend ping frontend
   ```

### Debug Mode

```bash
# Run with debug logging
docker-compose -f docker-compose.debug.yml up

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 📈 Performance Optimization

### 1. Resource Allocation

```yaml
# Optimal resource allocation for production
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  frontend:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### 2. Caching Strategy

```bash
# Enable Redis for caching (optional)
docker run -d --name redis \
  --network ecosmart-network \
  redis:alpine

# Configure backend to use Redis
# Add to backend environment:
REDIS_URL=redis://redis:6379
```

## 📋 Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Health checks enabled
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Security headers configured
- [ ] Resource limits set
- [ ] Log rotation enabled
- [ ] Load testing completed
- [ ] Deployment tested

## 🔗 Useful Commands

```bash
# Full system restart
docker-compose down && docker-compose up -d

# Clean rebuild
docker-compose build --no-cache
docker-compose up -d

# View all container logs
docker-compose logs -f --tail=100

# Remove everything (DANGER!)
docker-compose down -v --rmi all
docker system prune -a
```

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `docker-compose exec backend ping frontend`
4. Review resource usage: `docker stats`

---

**🌟 EcoSmart AI is now ready for production deployment!** 🇲🇦⚡ 