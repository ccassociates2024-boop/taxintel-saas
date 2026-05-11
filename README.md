# Indian AI-Powered Tax Intelligence Platform

Complete deployable MVP for CA firms, tax consultants, and financial advisors.

## Stack

- Frontend: Next.js 14, TypeScript, Tailwind CSS, ShadCN-style UI
- Backend: FastAPI, JWT auth, REST APIs
- Database: PostgreSQL
- AI: OpenAI API integration with deterministic rule fallback
- Files: PDF, JSON, Excel parsing with OCR-ready architecture
- Deployment: Docker Compose, Railway backend, Vercel frontend

## Run Locally

```bash
docker-compose up --build
```

Open:

```txt
Frontend: http://localhost:3000
Backend API docs: http://localhost:8000/docs
```

Register a user, create a client, upload AIS/26AS files, run recommendations, and download reports.

## Environment

Backend variables are documented in [backend/.env.example](backend/.env.example).
Frontend variables are documented in [frontend/.env.example](frontend/.env.example).

To enable OpenAI recommendations:

```bash
OPENAI_API_KEY=sk-your-key docker-compose up --build
```

## Folders

```txt
frontend/   Next.js SaaS UI
backend/    FastAPI API, auth, parsers, tax engine, AI recommendations
ai-engine/  AI extraction/split-out notes for scale
database/   PostgreSQL schema
docker/     Alternate Dockerfiles
docs/       API and deployment documentation
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## API

See [docs/API.md](docs/API.md).

