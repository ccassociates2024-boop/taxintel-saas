# AI Engine

The MVP embeds the Python AI recommendation engine in the FastAPI backend under `backend/app/services/recommendations.py` so the app is easy to deploy on Railway.

For scale, split this folder into a separate worker or FastAPI service and reuse the deterministic tax/recommendation payloads from the backend.

Suggested production split:

```txt
ai-engine/
  app/
    main.py
    services/openai_advisor.py
    services/risk_rules.py
    schemas.py
```

