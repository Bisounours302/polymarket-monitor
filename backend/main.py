from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os

from database import get_session, Alert, GlobalSettings

app = FastAPI(title="Polymarket Monitor API")

# CORS (Allow Frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class AlertSchema(BaseModel):
    id: int
    timestamp: datetime
    market_name: str
    amount_usd: float
    wallet_address: str
    nonce: int
    polymarket_url: str
    tx_hash: str
    
    class Config:
        orm_mode = True

class SettingsSchema(BaseModel):
    notify_whales: bool
    notify_suspicious: bool
    system_active: bool

# ... (existing code)

# ... (existing code)

# Dependency
def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get current notification settings."""
    whales = db.query(GlobalSettings).filter_by(key="notify_whales").first()
    suspicious = db.query(GlobalSettings).filter_by(key="notify_suspicious").first()
    system = db.query(GlobalSettings).filter_by(key="system_active").first()
    
    return {
        "notify_whales": whales.value.lower() == "true" if whales else True,
        "notify_suspicious": suspicious.value.lower() == "true" if suspicious else True,
        "system_active": system.value.lower() == "true" if system else True
    }

@app.post("/settings")
def update_settings(settings: SettingsSchema, db: Session = Depends(get_db)):
    """Update notification settings."""
    # Helper to update/create
    def update_key(key, val):
        obj = db.query(GlobalSettings).filter_by(key=key).first()
        if not obj:
            obj = GlobalSettings(key=key, value=str(val).lower())
            db.add(obj)
        else:
            obj.value = str(val).lower()

    update_key("notify_whales", settings.notify_whales)
    update_key("notify_suspicious", settings.notify_suspicious)
    update_key("system_active", settings.system_active)
    
    db.commit()
    return {"status": "updated", "settings": settings}

# Debug Endpoints
@app.get("/debug/markets")
def debug_markets():
    from worker import fetch_markets
    try:
        data = fetch_markets()
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/trades")
def debug_trades(market_id: str):
    from worker import fetch_trades_graphql
    import time
    try:
        # Fetch trades from the last 24 hours for debugging
        one_day_ago = time.time() - (24 * 3600)
        data = fetch_trades_graphql(market_id, timestamp_from=one_day_ago)
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
