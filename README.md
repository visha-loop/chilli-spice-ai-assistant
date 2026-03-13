# Chilli Spice AI Assistant

Chilli Spice is a demo-ready restaurant AI assistant built for freelancing showcase work.
It combines a bold campaign-style frontend with a practical restaurant operations backend.

## What It Does

- Premium landing page with a strong restaurant brand presentation
- AI concierge chat for menu questions and dish recommendations
- Multi-cuisine menu across Indian, Italian, and Chinese dishes
- Reservation booking flow for customers
- Staff dashboard with login, filters, reservation statuses, and internal notes
- JSON-based storage for easy local demos

## Stack

- Backend: FastAPI
- Frontend: HTML, CSS, JavaScript
- Data store: JSON
- Deployment target:
  - Frontend: Vercel
  - Backend: Render

## Project Structure

- `backend/main.py` FastAPI app, admin auth, chat flow, reservation APIs
- `frontend/index.html` main marketing-style restaurant landing page
- `frontend/admin.html` staff reservations dashboard
- `frontend/app.js` customer-side interactions
- `frontend/admin.js` staff dashboard logic
- `frontend/styles.css` main site styling
- `frontend/admin.css` dashboard styling
- `data/menu.json` menu knowledge base
- `data/reservations.json` reservation records
- `vercel.json` frontend deployment and API proxy config
- `render.yaml` backend deployment config

## Local Run

```bash
cd /Users/vishal.p/Desktop/chilli-spice-ai-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:

- Customer site: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Staff dashboard: [http://127.0.0.1:8000/admin.html](http://127.0.0.1:8000/admin.html)

## Staff Login

Default local demo credentials:

- Username: `manager`
- Password: `chilli-spice-admin`

For production, set your own environment variables:

```bash
export CHILLI_SPICE_ADMIN_USERNAME="manager"
export CHILLI_SPICE_ADMIN_PASSWORD="replace-this-password"
```

## Deployment

### Render Backend

This repo already includes [render.yaml](./render.yaml).

Set these environment variables on Render:

- `CHILLI_SPICE_ADMIN_USERNAME`
- `CHILLI_SPICE_ADMIN_PASSWORD`

Start command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Vercel Frontend

This repo already includes [vercel.json](./vercel.json).

It rewrites `/api/*` requests to:

- `https://chilli-spice-ai-assistant.onrender.com`

After deploying the backend on Render with that service name, you can import this GitHub repo into Vercel and deploy directly.

## API Overview

- `GET /api/health`
- `GET /api/menu`
- `POST /api/chat`
- `POST /api/reservations`
- `POST /api/admin/login`
- `GET /api/admin/reservations`
- `PATCH /api/admin/reservations/{reservation_id}`

## Demo Notes

- Reservation data is stored in `data/reservations.json`
- Menu knowledge is stored in `data/menu.json`
- The staff dashboard supports:
  - reservation filters
  - status changes
  - internal notes
  - summary cards for total bookings, today, new, confirmed, and covers

## Preview Assets

Food visuals used in the app live in:

- `frontend/assets/photos/`

I was not able to capture live browser screenshots from this terminal environment, so README screenshots can be added after deployment from your local browser view.
