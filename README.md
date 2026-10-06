# Reflective Listening Prototype

See `docs/prd-reflective-listening.md` for the spec and `docs/prototype-log.md` for every
place the build diverges from it (naming, schema, scoping).

## One-time setup

```sh
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

To enable the AI review step, create `backend/.env`:

```
OPENAI_API_KEY=sk-...
```

Without it, everything works except `POST /voice_memos/{id}/review` (the AI-proposed RQ
connections). faster-whisper downloads its model (`small.en`, ~500MB) on first
transcription — needs network once, runs local after that.

```sh
cd frontend
npm install
```

## Running it

```sh
# backend (from backend/, with .venv active)
uvicorn app.main:app --port 8000

# frontend (from frontend/)
npm run dev
```

Open http://localhost:5173. The reader is scoped to the two conversations under project 5
(the only project in the snapshot with a real conversation guide — see the prototype log).

## Tests

```sh
cd backend && source .venv/bin/activate && python -m pytest
```

Tests run against a scratch database (see `tests/conftest.py`) and the real, read-only
Cortico snapshot — they never touch `db/prototype.db`.
