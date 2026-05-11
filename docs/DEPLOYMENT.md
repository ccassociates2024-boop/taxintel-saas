# Deployment Guide

## Local Docker

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
docker-compose up --build
```

Open:

```txt
Frontend: http://localhost:3000
Backend:  http://localhost:8000/docs
```

## Railway Backend

1. Create a Railway project.
2. Add a PostgreSQL database.
3. Add a backend service from this repository.
4. Set the service root to `backend` if using Railway UI, or use the root `railway.toml`.
5. Add environment variables:

```txt
DATABASE_URL=<Railway PostgreSQL SQLAlchemy URL>
JWT_SECRET=<strong random secret>
CORS_ORIGINS=https://your-vercel-domain.vercel.app
OPENAI_API_KEY=<your key>
OPENAI_MODEL=gpt-4.1
ENABLE_OPENAI=true
```

Railway usually provides a Postgres URL like `postgresql://...`. For this app, use:

```txt
postgresql+psycopg://...
```

## Vercel Frontend

1. Import the repo in Vercel.
2. Set root directory to `frontend`.
3. Add environment variable:

```txt
NEXT_PUBLIC_API_URL=https://your-railway-backend.up.railway.app
```

4. Deploy.

## OpenAI Key

Set `OPENAI_API_KEY` in Railway for production or in your shell for local Docker:

```bash
OPENAI_API_KEY=sk-... docker-compose up --build
```

Without the key, the app still returns rule-based recommendations.

