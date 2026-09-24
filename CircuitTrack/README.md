# CircuitTrack

CircuitTrack is an electronics repair management system for Missouri S&T CS2300.

## Production-ready stack
- React + Vite
- FastAPI
- SQLAlchemy
- PostgreSQL in production (Neon)
- SQLite fallback for local development
- Docker
- Render deployment blueprint

## Main workflow
Customer -> Device -> Repair Job -> Technician / Diagnostics / Parts -> Completed Repair

## Run locally

### Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Deploy

See [DEPLOY.md](DEPLOY.md).

## Database

The application creates the schema automatically from the SQLAlchemy models.
A PostgreSQL SQL version is also included at:

`backend/database.sql`
