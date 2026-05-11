# SprintHub — Collaborative Project Tracker

A full-stack project and work-item management platform with role-based permissions.

## Technology Stack
- **Backend:** FastAPI + PostgreSQL + SQLAlchemy ORM + JWT Auth
- **Frontend:** Vanilla React (via CDN) — single-file, no build tooling required
- **Deployment:** Railway platform (backend + frontend as separate services)

## Getting Started Locally

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Fill in your DATABASE_URL and SECRET_KEY in .env
uvicorn main:app --reload
```
API available at: http://localhost:8000  
Interactive docs at: http://localhost:8000/docs

### Frontend Setup
```bash
# Simply open frontend/index.html in your browser, or:
python -m http.server 5173 --directory frontend
```

## Deploying to Railway

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "first commit"
git remote add origin https://github.com/YOUR_USERNAME/sprinthub
git push -u origin main
```

### Step 2: Deploy the Backend
1. Visit railway.app → New Project → Deploy from GitHub repo
2. Select your repository
3. Set root directory to `backend`
4. Add a PostgreSQL addon
5. Configure environment variables:
   - `DATABASE_URL` → auto-set when PostgreSQL is linked
   - `SECRET_KEY` → a random string, at least 32 characters
   - `FRONTEND_URL` → your deployed frontend URL

### Step 3: Deploy the Frontend
1. New service → same GitHub repo
2. Root directory: `frontend`
3. Start command: `python -m http.server $PORT`
4. Set `API_BASE_URL` env var to your backend's Railway URL

## Feature Overview
- ✅ JWT-based Auth (Sign Up / Sign In / Token Refresh)
- ✅ Role-Based Access Control (Admin / Member)
- ✅ Workspace Management (CRUD + colour themes)
- ✅ Work Item Tracking (CRUD + status/priority)
- ✅ Kanban Board
- ✅ Team Membership Management
- ✅ Dashboard with metrics and activity feed
- ✅ Due date tracking with overdue alerts
- ✅ Threaded comments on work items
- ✅ Full REST API with auto-generated docs at /docs

## REST API Reference
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET  /api/v1/auth/me
- GET  /api/v1/workspaces
- POST /api/v1/workspaces
- GET  /api/v1/workspaces/{id}
- PATCH /api/v1/workspaces/{id}
- DELETE /api/v1/workspaces/{id}
- POST /api/v1/workspaces/{id}/members
- DELETE /api/v1/workspaces/{id}/members/{uid}
- GET  /api/v1/workspaces/{id}/items
- POST /api/v1/workspaces/{id}/items
- PATCH /api/v1/workspaces/{id}/items/{iid}
- DELETE /api/v1/workspaces/{id}/items/{iid}
- GET  /api/v1/dashboard/summary
- GET  /api/v1/dashboard/feed
- GET  /api/v1/dashboard/assigned
