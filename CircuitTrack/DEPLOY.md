# Deploy CircuitTrack

This version is prepared for a single public Render URL.

Production architecture:

Browser -> Render Docker Web Service -> FastAPI -> Neon PostgreSQL
                    |
                    +-> React static frontend

The React app and FastAPI API are served from the same Render service, so there is
no production CORS configuration and no frontend API URL to edit.

## What you need

- A GitHub account
- A free Neon account
- A free Render account

## Step 1 - Put the project on GitHub

Create an empty GitHub repository named `CircuitTrack`.

From PowerShell in the folder that contains this README:

```powershell
git init
git add .
git commit -m "Initial CircuitTrack deployment"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

If Git is not installed:

```powershell
winget install --id Git.Git -e
```

Close and reopen PowerShell after installing Git.

## Step 2 - Create the PostgreSQL database in Neon

1. Sign in to Neon.
2. Create a new project named `CircuitTrack`.
3. Open the project's Connect panel.
4. Copy the PostgreSQL connection string.
5. Keep it private. Do not paste it into GitHub or commit it to a file.

The app accepts Neon's standard `postgresql://...` connection string directly.

## Step 3 - Deploy with Render Blueprint

1. Sign in to Render and connect your GitHub account.
2. Create a new Blueprint from the CircuitTrack repository.
3. Render will detect `render.yaml`.
4. When Render asks for `DATABASE_URL`, paste the Neon connection string.
5. Apply/Create the Blueprint.
6. Wait for the Docker build and deploy to finish.
7. Open the generated `https://...onrender.com` URL.

The application automatically:
- creates the relational tables on first startup,
- seeds demo data only if the Customer table is empty,
- serves React at `/`,
- serves FastAPI at `/api`,
- exposes health status at `/api/health`,
- exposes API documentation at `/docs`.

## Updating the public site later

After changing files locally:

```powershell
git add .
git commit -m "Update CircuitTrack"
git push
```

Render will redeploy from the Git repository.

## Local development

Backend:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Frontend in a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Vite automatically proxies `/api` requests to the local FastAPI server.

## Useful public URLs after deployment

- App: `https://YOUR-RENDER-SERVICE.onrender.com/`
- Health check: `https://YOUR-RENDER-SERVICE.onrender.com/api/health`
- Swagger API docs: `https://YOUR-RENDER-SERVICE.onrender.com/docs`

## Notes

- The database connection string is a secret.
- Do not commit `.env`.
- `database.sql` is included as a PostgreSQL schema file for the course project.
- The free Render web service may need time to wake after being idle.
