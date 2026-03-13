from __future__ import annotations

import json
import math
import os
import re
import secrets
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
MENU_PATH = DATA_DIR / "menu.json"
RESERVATIONS_PATH = DATA_DIR / "reservations.json"

ADMIN_USERNAME = os.getenv("CHILLI_SPICE_ADMIN_USERNAME", "manager")
ADMIN_PASSWORD = os.getenv("CHILLI_SPICE_ADMIN_PASSWORD", "chilli-spice-admin")
ADMIN_TOKENS: dict[str, str] = {}

REQUIRED_RESERVATION_FIELDS = ["name", "phone", "date", "time", "guests"]
RESERVATION_STATUSES = {"new", "confirmed", "seated", "completed", "cancelled"}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ReservationRequest(BaseModel):
    name: str = Field(min_length=2)
    phone: str = Field(min_length=7)
    date: str = Field(min_length=8)
    time: str = Field(min_length=4)
    guests: int = Field(ge=1, le=20)
    special_requests: str = ""


class ReservationUpdateRequest(BaseModel):
    status: str | None = None
    internal_notes: str | None = None


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class SessionState(BaseModel):
    pending_intent: str | None = None
    reservation_draft: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, str]] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_menu() -> list[dict[str, Any]]:
    with MENU_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload["menu"]


def normalize_reservation(item: dict[str, Any], fallback_id: int) -> dict[str, Any]:
    reservation = dict(item)
    reservation["id"] = int(reservation.get("id", fallback_id))
    reservation["name"] = reservation.get("name", "")
    reservation["phone"] = reservation.get("phone", "")
    reservation["date"] = reservation.get("date", "")
    reservation["time"] = reservation.get("time", "")
    reservation["guests"] = int(reservation.get("guests", 1))
    reservation["special_requests"] = reservation.get("special_requests", "")
    reservation["status"] = reservation.get("status", "new")
    if reservation["status"] not in RESERVATION_STATUSES:
        reservation["status"] = "new"
    reservation["internal_notes"] = reservation.get("internal_notes", "")
    reservation["created_at"] = reservation.get("created_at", utc_now_iso())
    return reservation


def load_reservations() -> list[dict[str, Any]]:
    if not RESERVATIONS_PATH.exists():
        return []
    with RESERVATIONS_PATH.open("r", encoding="utf-8") as file:
        raw = json.load(file)
    return [normalize_reservation(item, index + 1) for index, item in enumerate(raw)]


def save_reservations(reservations: list[dict[str, Any]]) -> None:
    normalized = [normalize_reservation(item, index + 1) for index, item in enumerate(reservations)]
    with RESERVATIONS_PATH.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())


def build_menu_document(item: dict[str, Any]) -> str:
    return " ".join(
        [
            item["name"],
            item.get("cuisine", ""),
            item["category"],
            item["description"],
            item.get("spice_level", ""),
            " ".join(item.get("tags", [])),
            " ".join(item.get("ingredients", [])),
            " ".join(item.get("allergens", [])),
            item.get("best_for", ""),
        ]
    )


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def infer_preferences(query: str) -> dict[str, Any]:
    lowered = query.lower()
    filters: dict[str, Any] = {
        "tags": set(),
        "exclude_tags": set(),
        "spice_level": None,
        "ingredients": set(),
        "category": None,
    }

    for tag in ["vegetarian", "vegan", "gluten-free", "popular"]:
        if tag in lowered:
            filters["tags"].add(tag)

    if "not spicy" in lowered or "mild" in lowered:
        filters["spice_level"] = "mild"
    elif "medium" in lowered:
        filters["spice_level"] = "medium"
    elif "spicy" in lowered or "hot" in lowered:
        filters["spice_level"] = "hot"

    category_map = {
        "starter": "Starter",
        "appetizer": "Starter",
        "main": "Main Course",
        "curry": "Main Course",
        "rice": "Rice",
        "bread": "Bread",
        "drink": "Beverage",
        "dessert": "Dessert",
        "pizza": "Pizza",
        "pasta": "Pasta",
        "noodles": "Noodles",
    }
    for key, value in category_map.items():
        if key in lowered:
            filters["category"] = value
            break

    for term in [
        "chicken",
        "lamb",
        "paneer",
        "cauliflower",
        "chickpeas",
        "rice",
        "mango",
        "naan",
        "mushroom",
        "pizza",
        "pasta",
        "noodles",
    ]:
        if term in lowered:
            filters["ingredients"].add(term)

    for cuisine in ["indian", "italian", "chinese"]:
        if cuisine in lowered:
            filters["tags"].add(cuisine)

    if "no dairy" in lowered or "dairy-free" in lowered:
        filters["exclude_tags"].add("contains-dairy")
    if "no nuts" in lowered or "nut-free" in lowered:
        filters["exclude_tags"].add("contains-nuts")

    return filters


MENU = load_menu()
MENU_VECTORS = [{"item": item, "tokens": Counter(tokenize(build_menu_document(item)))} for item in MENU]
SESSIONS: dict[str, SessionState] = {}


def score_menu_item(query: str, item: dict[str, Any], vector: Counter[str]) -> float:
    score = cosine_similarity(Counter(tokenize(query)), vector)
    preferences = infer_preferences(query)
    tags = {tag.lower() for tag in item.get("tags", [])}
    ingredients = " ".join(item.get("ingredients", [])).lower()
    cuisine = item.get("cuisine", "").lower()

    if preferences["category"] and item["category"] == preferences["category"]:
        score += 0.6
    if preferences["spice_level"] and item.get("spice_level") == preferences["spice_level"]:
        score += 0.8
    if preferences["spice_level"] == "hot" and item.get("spice_level") == "medium":
        score += 0.3
    if preferences["tags"].issubset(tags):
        score += 1.2
    for tag in preferences["tags"]:
        if tag in tags:
            score += 0.5
        if tag == cuisine:
            score += 1.0
    for ingredient in preferences["ingredients"]:
        if ingredient in item["name"].lower() or ingredient in ingredients:
            score += 0.7
    for blocked_tag in preferences["exclude_tags"]:
        if blocked_tag in tags:
            score -= 2.0
    if "recommend" in query.lower() or "suggest" in query.lower():
        if "popular" in tags:
            score += 0.6
    return score


def retrieve_menu_items(query: str, limit: int = 4) -> list[dict[str, Any]]:
    preferences = infer_preferences(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    cuisine_filters = {tag for tag in preferences["tags"] if tag in {"indian", "italian", "chinese"}}
    for entry in MENU_VECTORS:
        item = entry["item"]
        cuisine = item.get("cuisine", "").lower()
        if cuisine_filters and cuisine not in cuisine_filters:
            continue
        if preferences["category"] and item["category"] != preferences["category"]:
            if preferences["category"] in {"Pizza", "Pasta", "Noodles"}:
                continue
        score = score_menu_item(query, item, entry["tokens"])
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def summarize_item(item: dict[str, Any]) -> str:
    tags = ", ".join(item.get("tags", [])[:3])
    return (
        f"{item['name']} ({item.get('cuisine', 'House')}) - INR {item['price']}. {item['description']} "
        f"Spice: {item['spice_level']}. Best for: {item.get('best_for', 'general dining')}."
        + (f" Tags: {tags}." if tags else "")
    )


def detect_reservation_intent(message: str, session: SessionState) -> bool:
    lowered = message.lower()
    if session.pending_intent == "reservation":
        return True
    return any(term in lowered for term in ["reservation", "reserve", "book a table", "book table", "table for"])


def extract_name(message: str) -> str | None:
    for pattern in [r"\bmy name is ([A-Za-z ]{2,})", r"\bthis is ([A-Za-z ]{2,})", r"\bname[: ]+([A-Za-z ]{2,})"]:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None


def extract_phone(message: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s-]{6,}\d)", message)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return None


def extract_date(message: str) -> str | None:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
    return match.group(1) if match else None


def extract_time(message: str) -> str | None:
    match = re.search(r"\b(\d{1,2}:\d{2})\b", message)
    if not match:
        return None
    hour, minute = match.group(1).split(":")
    return f"{int(hour):02d}:{minute}"


def extract_guests(message: str) -> int | None:
    for pattern in [r"\bfor (\d{1,2})\b", r"\b(\d{1,2}) guests?\b", r"\bparty of (\d{1,2})\b"]:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_special_requests(message: str) -> str | None:
    lowered = message.lower()
    triggers = ["window", "birthday", "quiet", "high chair", "allergy", "anniversary", "outdoor"]
    return message.strip() if any(trigger in lowered for trigger in triggers) else None


def update_reservation_draft(message: str, draft: dict[str, Any]) -> dict[str, Any]:
    extracted = {
        "name": extract_name(message),
        "phone": extract_phone(message),
        "date": extract_date(message),
        "time": extract_time(message),
        "guests": extract_guests(message),
        "special_requests": extract_special_requests(message),
    }
    for key, value in extracted.items():
        if value not in (None, ""):
            draft[key] = value
    return draft


def validate_reservation_fields(draft: dict[str, Any]) -> str | None:
    try:
        if "date" in draft:
            datetime.strptime(draft["date"], "%Y-%m-%d")
        if "time" in draft:
            datetime.strptime(draft["time"], "%H:%M")
    except ValueError:
        return "Please use date as YYYY-MM-DD and time as HH:MM."
    guests = draft.get("guests")
    if guests is not None and not 1 <= int(guests) <= 20:
        return "Reservations can be made for between 1 and 20 guests."
    return None


def next_missing_field(draft: dict[str, Any]) -> str | None:
    for field in REQUIRED_RESERVATION_FIELDS:
        if not draft.get(field):
            return field
    return None


def reservation_prompt_for(field: str) -> str:
    prompts = {
        "name": "I can book that for you. What name should I place the reservation under?",
        "phone": "What phone number should I attach to the reservation?",
        "date": "What date would you like? Please use YYYY-MM-DD.",
        "time": "What time should I book? Please use HH:MM.",
        "guests": "How many guests should I reserve the table for?",
    }
    return prompts[field]


def reservation_summary(draft: dict[str, Any]) -> str:
    return f"{draft['name']} on {draft['date']} at {draft['time']} for {draft['guests']} guests"


def create_reservation_record(payload: dict[str, Any]) -> dict[str, Any]:
    reservations = load_reservations()
    reservation = normalize_reservation(
        {
            "id": len(reservations) + 1,
            "name": payload["name"],
            "phone": payload["phone"],
            "date": payload["date"],
            "time": payload["time"],
            "guests": int(payload["guests"]),
            "special_requests": payload.get("special_requests", ""),
            "status": "new",
            "internal_notes": "",
            "created_at": utc_now_iso(),
        },
        len(reservations) + 1,
    )
    reservations.append(reservation)
    save_reservations(reservations)
    return reservation


def respond_with_menu_context(message: str) -> dict[str, Any]:
    matches = retrieve_menu_items(message)
    if not matches:
        return {
            "answer": (
                "I can help with curries, pizzas, noodles, drinks, and table bookings. "
                "Try asking for spicy dishes, vegetarian mains, or something good for a first visit."
            ),
            "sources": [],
            "chips": ["Show popular dishes", "Suggest a vegetarian dinner", "Book a table"],
        }

    lead = "Here are the strongest fits from the menu:" if any(
        word in message.lower() for word in ["recommend", "suggest", "best", "popular", "good for"]
    ) else "Here’s what matches your question from the menu:"

    return {
        "answer": "\n".join([lead] + [f"- {summarize_item(item)}" for item in matches[:3]]),
        "sources": matches[:3],
        "chips": ["Anything mild?", "Show vegan options", "I want to reserve a table"],
    }


def generate_chat_response(message: str, session: SessionState) -> dict[str, Any]:
    session.history.append({"role": "user", "content": message})

    if detect_reservation_intent(message, session):
        session.pending_intent = "reservation"
        session.reservation_draft = update_reservation_draft(message, session.reservation_draft)
        validation_error = validate_reservation_fields(session.reservation_draft)
        if validation_error:
            return {"answer": validation_error, "sources": [], "chips": []}

        missing = next_missing_field(session.reservation_draft)
        if missing:
            return {"answer": reservation_prompt_for(missing), "sources": [], "chips": []}

        reservation = create_reservation_record(session.reservation_draft)
        session.pending_intent = None
        session.reservation_draft = {}
        return {
            "answer": (
                f"Your table is booked for {reservation_summary(reservation)}. "
                "If you have a seating preference or celebration note, tell me and I can add it."
            ),
            "sources": [],
            "chips": ["Show popular dishes", "What goes well with naan?"],
        }

    if set(tokenize(message)) & {"hello", "hi", "hey"}:
        return {
            "answer": (
                "Welcome to Chilli Spice. I can recommend dishes from the menu, help with dietary preferences, and book a table for you."
            ),
            "sources": [],
            "chips": ["Recommend something spicy", "Show vegetarian mains", "Reserve a table for 4"],
        }

    return respond_with_menu_context(message)


def build_admin_summary(reservations: list[dict[str, Any]]) -> dict[str, Any]:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "total": len(reservations),
        "today": sum(1 for item in reservations if item["date"] == today),
        "new": sum(1 for item in reservations if item["status"] == "new"),
        "confirmed": sum(1 for item in reservations if item["status"] == "confirmed"),
        "covers": sum(item["guests"] for item in reservations),
    }


def require_admin_token(x_admin_token: str | None) -> str:
    if not x_admin_token or x_admin_token not in ADMIN_TOKENS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return ADMIN_TOKENS[x_admin_token]


def filter_reservations(
    reservations: list[dict[str, Any]],
    date: str | None,
    status: str | None,
    query: str | None,
) -> list[dict[str, Any]]:
    filtered = reservations
    if date:
        filtered = [item for item in filtered if item["date"] == date]
    if status and status != "all":
        filtered = [item for item in filtered if item["status"] == status]
    if query:
        needle = query.lower()
        filtered = [
            item
            for item in filtered
            if needle in item["name"].lower()
            or needle in item["phone"].lower()
            or needle in item["special_requests"].lower()
            or needle in item["internal_notes"].lower()
        ]
    return sorted(filtered, key=lambda item: (item["date"], item["time"], item["id"]))


app = FastAPI(title="Chilli Spice AI Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/menu")
def get_menu() -> dict[str, Any]:
    categories = sorted({item["category"] for item in MENU})
    cuisines = sorted({item.get("cuisine", "House") for item in MENU})
    return {"menu": MENU, "categories": categories, "cuisines": cuisines}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    session_id = request.session_id or str(uuid4())
    session = SESSIONS.setdefault(session_id, SessionState())
    response = generate_chat_response(request.message, session)
    response["session_id"] = session_id
    return response


@app.post("/api/reservations")
def create_reservation(request: ReservationRequest) -> dict[str, Any]:
    payload = request.model_dump()
    validation_error = validate_reservation_fields(payload)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)
    reservation = create_reservation_record(payload)
    return {"message": f"Reservation confirmed for {reservation_summary(reservation)}.", "reservation": reservation}


@app.get("/api/reservations")
def get_reservations() -> dict[str, Any]:
    return {"message": "Reservations are available through the staff dashboard."}


@app.post("/api/admin/login")
def admin_login(request: AdminLoginRequest) -> dict[str, Any]:
    if request.username != ADMIN_USERNAME or request.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(24)
    ADMIN_TOKENS[token] = request.username
    return {
        "token": token,
        "user": {"username": request.username, "role": "Restaurant Manager"},
        "summary": build_admin_summary(load_reservations()),
    }


@app.get("/api/admin/reservations")
def get_admin_reservations(
    x_admin_token: str | None = Header(default=None),
    date: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    reservations = filter_reservations(load_reservations(), date=date, status=status, query=q)
    return {
        "reservations": reservations,
        "summary": build_admin_summary(reservations),
        "statuses": sorted(RESERVATION_STATUSES),
    }


@app.patch("/api/admin/reservations/{reservation_id}")
def update_admin_reservation(
    reservation_id: int,
    request: ReservationUpdateRequest,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    reservations = load_reservations()
    target = next((item for item in reservations if item["id"] == reservation_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if request.status is not None:
        if request.status not in RESERVATION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid reservation status")
        target["status"] = request.status
    if request.internal_notes is not None:
        target["internal_notes"] = request.internal_notes.strip()
    save_reservations(reservations)
    return {"reservation": target, "message": f"Reservation #{reservation_id} updated."}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
