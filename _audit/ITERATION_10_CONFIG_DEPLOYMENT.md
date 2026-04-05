# Audit Iteration 10 - Config & Deployment

## Issues Found: 8

### CD-01: .env.example missing 3 settings variables [FIXED]
- `COSIUM_ACCESS_TOKEN`, `COSIUM_DEVICE_CREDENTIAL`, `MAX_UPLOAD_SIZE_MB` were in Settings but not in .env.example
- Added all three with appropriate comments

### CD-02: docker-compose.yml missing restart policies [FIXED]
- No `restart:` directive on any service - containers would not restart after crash or host reboot
- Added `restart: unless-stopped` to all 7 services (postgres, redis, minio, mailhog, api, web, worker, beat)

### CD-03: docker-compose.yml web service missing health check [FIXED]
- The `web` service had no healthcheck, unlike all other services
- Added wget-based health check (consistent with docker-compose.prod.yml)
- Also changed `depends_on: [api]` to use `condition: service_healthy`

### CD-04: README.md outdated component counts [FIXED]
- Routers: 29 -> 32, Services: 34 -> 37, Repos: 18 -> 19
- Schemas: 20 -> 27, Models: 15 -> 17, Migrations: 18 -> 24
- Backend tests: 44 files (338+) -> 71 files (488+)
- Frontend tests: 10 files (70+) -> 26 files
- Frontend pages: 31 -> 43
- Fixed CONTRIBUTING.md reference (file doesn't exist) -> CLAUDE.md

### CD-05: Frontend Dockerfile.prod not using standalone output [FIXED]
- next.config.ts sets `output: "standalone"` but Dockerfile.prod copied full node_modules (~200MB)
- Replaced with standalone build copy pattern (server.js + static + public) - typically ~30MB
- Added non-root user (appuser) for security

### CD-06: GitHub Actions CI properly configured [CLEAN]
- ci.yml covers: backend lint, backend test, frontend lint+typecheck, frontend test, docker build
- Uses service containers for postgres, redis, minio
- Caches npm with package-lock.json
- Runs on push to main/develop and PRs to main

### CD-07: Lockfiles committed [CLEAN]
- `frontend/package-lock.json` exists and is committed
- `backend/requirements.txt` uses pinned versions (==)

### CD-08: .dockerignore files present [CLEAN]
- Both `backend/.dockerignore` and `frontend/.dockerignore` exist
- Backend excludes: __pycache__, tests/, .pytest_cache, .coverage
- Frontend excludes: node_modules, .next

## Summary
- Issues found: 8
- Issues fixed: 5
- Clean checks: 3
