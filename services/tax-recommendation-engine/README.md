# AI Tax Recommendation Engine

Python FastAPI service for Indian tax recommendation workflows. It accepts AIS, 26AS, salary, capital gains, business income, and claimed deduction data, then returns deterministic tax analysis plus an optional OpenAI-generated consultation summary.

The engine deliberately keeps tax math deterministic and uses OpenAI only for structured explanation, prioritization, and CA/client-ready narrative.

## Features

- Old vs new regime optimization
- Missing deduction detection
- Tax-saving opportunities
- Scrutiny risk analysis
- Advance tax suggestions
- Consultation summary using OpenAI structured outputs
- FastAPI REST API
- Unit-testable deterministic core

## Local Setup

```bash
cd services/tax-recommendation-engine
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload --port 8010
```

## Environment

```txt
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1
ENABLE_OPENAI=true
```

If `OPENAI_API_KEY` is missing or `ENABLE_OPENAI=false`, the service still returns deterministic recommendations with a local summary.

