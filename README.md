# Chilli Spice AI Assistant

Chilli Spice is a full-stack restaurant AI assistant built as a freelancing-ready showcase project.  
It combines a bold campaign-style landing page, AI-powered menu guidance, a reservation workflow, and a staff dashboard for managing bookings.

## Live Demo

- Frontend: [chilli-spice-ai-assistant-ahab-eoeghmik7.vercel.app](https://chilli-spice-ai-assistant-ahab-eoeghmik7.vercel.app)
- Backend: [chilli-spice-ai-assistant.onrender.com](https://chilli-spice-ai-assistant.onrender.com)
- Staff dashboard: [chilli-spice-ai-assistant-ahab-eoeghmik7.vercel.app/admin](https://chilli-spice-ai-assistant-ahab-eoeghmik7.vercel.app/admin)

## Highlights

- Premium restaurant landing page with a launch-style visual direction
- AI concierge for menu discovery and dish recommendations
- Reservation booking via form and conversational AI chat
- Multi-cuisine menu with Indian, Italian, and Chinese dishes
- Staff operations dashboard with login, filters, status changes, notes, and delete actions
- JSON-based persistence for lightweight demos and prototypes

## Tech Stack

- FastAPI
- HTML, CSS, JavaScript
- JSON data storage
- Render for backend deployment
- Vercel for frontend deployment

## Product Preview

To render screenshots in GitHub, place your exported images in:

- `docs/screenshots/homepage.png`
- `docs/screenshots/menu-slider.png`
- `docs/screenshots/ai-chat.png`
- `docs/screenshots/admin-dashboard.png`

Once those files are added, this section will render automatically:

```md
## Product Preview

![Homepage Hero](docs/screenshots/homepage.png)
![Menu Slider](docs/screenshots/menu-slider.png)
![AI Chat](docs/screenshots/ai-chat.png)
![Admin Dashboard](docs/screenshots/admin-dashboard.png)
```

Recommended screenshots:

1. Homepage hero section with the `CHILLI SPICE` headline
2. Menu slider section with food cards
3. AI concierge and reservation form layout
4. Staff dashboard showing summary cards and reservation table

## Features

### Customer Experience

- Explore the menu through a premium landing page
- Ask the AI chat for recommendations and menu help
- Book a reservation from the form or through conversational prompts

### Restaurant Operations

- Staff login for admin access
- Filter reservations by date, status, or search term
- Update reservation status
- Add internal notes
- Delete test or demo reservations directly from the dashboard

## Project Structure

- `backend/main.py` FastAPI app, chat logic, reservation logic, admin APIs
- `frontend/index.html` main restaurant landing page
- `frontend/admin.html` staff dashboard
- `frontend/app.js` customer-side interactions
- `frontend/admin.js` staff dashboard logic
- `frontend/styles.css` landing page styling
- `frontend/admin.css` admin dashboard styling
- `data/menu.json` menu data used by the assistant
- `data/reservations.json` reservation records
- `render.yaml` Render deployment config
- `vercel.json` Vercel static frontend config and API proxy

## Local Development

```bash
cd /Users/vishal.p/Desktop/chilli-spice-ai-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open locally:

- Customer site: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Staff dashboard: [http://127.0.0.1:8000/admin.html](http://127.0.0.1:8000/admin.html)

## Admin Login

The app uses environment variables for production credentials:

- `CHILLI_SPICE_ADMIN_USERNAME`
- `CHILLI_SPICE_ADMIN_PASSWORD`

Local/demo defaults in code:

- Username: `manager`
- Password: `chilli-spice-admin`

## Deployment Notes

### Render

Use:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Set:

- `CHILLI_SPICE_ADMIN_USERNAME`
- `CHILLI_SPICE_ADMIN_PASSWORD`

### Vercel

The frontend is configured as a static deployment.  
`vercel.json` rewrites `/api/*` to the Render backend URL.

## API Endpoints

- `GET /api/health`
- `GET /api/menu`
- `POST /api/chat`
- `POST /api/reservations`
- `POST /api/admin/login`
- `GET /api/admin/reservations`
- `PATCH /api/admin/reservations/{reservation_id}`
- `DELETE /api/admin/reservations/{reservation_id}`
