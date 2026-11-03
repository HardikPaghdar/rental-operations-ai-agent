from datetime import date
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Rental Operations AI Agent", version="0.1.0",
              description="Synthetic rental operations API with human-in-the-loop recommendations.")

INVENTORY = [
    {"id": "beach-chair-01", "name": "Premium Beach Chair", "category": "beach", "daily_rate": 12.0, "total_units": 20, "maintenance": False},
    {"id": "umbrella-02", "name": "Large Beach Umbrella", "category": "beach", "daily_rate": 18.0, "total_units": 12, "maintenance": False},
    {"id": "golf-cart-03", "name": "4-seat Golf Cart", "category": "vehicle", "daily_rate": 95.0, "total_units": 5, "maintenance": True},
    {"id": "kayak-04", "name": "Single Kayak", "category": "water-sports", "daily_rate": 38.0, "total_units": 8, "maintenance": False},
]
BOOKINGS = [
    {"id": "BK-201", "item_id": "beach-chair-01", "quantity": 6, "start": "2026-11-10", "end": "2026-11-12", "status": "confirmed"},
    {"id": "BK-202", "item_id": "beach-chair-01", "quantity": 8, "start": "2026-11-11", "end": "2026-11-13", "status": "confirmed"},
    {"id": "BK-203", "item_id": "umbrella-02", "quantity": 4, "start": "2026-11-10", "end": "2026-11-11", "status": "confirmed"},
]

class QuoteRequest(BaseModel):
    item_id: str
    quantity: int = Field(gt=0, le=100)
    days: int = Field(gt=0, le=90)

class RecommendationRequest(BaseModel):
    scenario: str
    booking_id: str | None = None
    hours_late: int = Field(default=0, ge=0)
    issue: str | None = None

@app.get("/health")
def health():
    return {"status": "ok", "mode": "synthetic-demo"}

@app.get("/inventory")
def inventory():
    return {"items": INVENTORY, "count": len(INVENTORY)}

@app.get("/bookings")
def bookings():
    return {"bookings": BOOKINGS}

@app.get("/availability")
def availability(item_id: str, start: date, end: date, quantity: int = Query(default=1, gt=0)):
    if end < start:
        raise HTTPException(422, "end must be on or after start")
    item = next((x for x in INVENTORY if x["id"] == item_id), None)
    if not item:
        raise HTTPException(404, "Unknown inventory item")
    overlapping = [b for b in BOOKINGS if b["item_id"] == item_id and b["status"] == "confirmed"
                   and b["start"] <= end.isoformat() and b["end"] >= start.isoformat()]
    reserved = sum(b["quantity"] for b in overlapping)
    available = max(0, item["total_units"] - reserved - (item["total_units"] if item["maintenance"] else 0))
    return {"item_id": item_id, "start": start, "end": end, "requested": quantity,
            "available": available, "is_available": available >= quantity,
            "overlapping_booking_ids": [b["id"] for b in overlapping],
            "note": "Static demo inventory; not a live reservation guarantee."}

@app.post("/quotes")
def create_quote(payload: QuoteRequest):
    item = next((x for x in INVENTORY if x["id"] == payload.item_id), None)
    if not item:
        raise HTTPException(404, "Unknown inventory item")
    subtotal = round(item["daily_rate"] * payload.quantity * payload.days, 2)
    service_fee = round(subtotal * 0.05, 2)
    return {"item": item["name"], "quantity": payload.quantity, "days": payload.days,
            "daily_rate": item["daily_rate"], "subtotal": subtotal, "service_fee": service_fee,
            "total": round(subtotal + service_fee, 2), "currency": "USD",
            "status": "quote_only", "expires_in_hours": 24}

@app.post("/agent/recommend")
def recommend(payload: RecommendationRequest):
    scenario = payload.scenario.lower().strip()
    if scenario == "late_return":
        action = "Contact the renter, confirm the revised return time, and check the next booking."
        reasons = [f"Return is reported {payload.hours_late} hour(s) late.",
                   "Check downstream reservations before extending the rental."]
        approval = True
    elif scenario == "maintenance":
        action = "Mark the item unavailable and assign a technician inspection."
        reasons = [payload.issue or "A maintenance issue was reported.",
                   "Do not re-rent equipment until an authorized inspection clears it."]
        approval = True
    elif scenario == "new_booking":
        action = "Check availability, verify renter details, then send a quote for approval."
        reasons = ["A new booking request needs inventory and customer verification."]
        approval = True
    else:
        raise HTTPException(422, "scenario must be late_return, maintenance, or new_booking")
    return {"scenario": scenario, "booking_id": payload.booking_id, "recommended_action": action,
            "reasoning": reasons, "requires_human_approval": approval,
            "execution": "not_performed", "mode": "deterministic_policy_demo"}

