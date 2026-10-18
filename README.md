# Hackathon iFood API

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
pytest
```

Docs: http://localhost:8000/docs
