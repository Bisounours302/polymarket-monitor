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

# ... existing code ...

# Dependency
def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "ok", "service": "backend", "message": "Polymarket Monitor API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/alerts", response_model=List[AlertSchema])
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch latest alerts."""
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).limit(limit).all()
    return alerts

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get aggregated stats."""
    from sqlalchemy import func
    total_alerts = db.query(func.count(Alert.id)).scalar()
    total_volume = db.query(func.sum(Alert.amount_usd)).scalar() or 0
    return {
        "total_alerts": total_alerts,
        "total_volume": round(total_volume, 2)
    }

@app.get("/settings")
# ... existing code ...
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
# Debug Endpoints
@app.get("/debug/markets")
def debug_markets():
    import json
    import os
    from polymarket import fetch_markets
    
    try:
        # Try reading the Worker's cache first
        cache_path = "/app/data/debug_markets.json"
        if not os.path.exists(cache_path):
            cache_path = "data/debug_markets.json" # Local fallback
            
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                return {"source": "cache", "count": len(data), "data": data}
            except json.JSONDecodeError:
                # Cache corrupted/empty, ignore and fallback
                pass
            
        # Fallback to direct fetch if cache missing or corrupt
        data = fetch_markets()
        return {"source": "live", "count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/feed")
def debug_feed():
    import json
    import os
    try:
        feed_path = "/app/data/live_feed.json"
        if not os.path.exists(feed_path):
            feed_path = "data/live_feed.json"
            
        if os.path.exists(feed_path):
            with open(feed_path, "r") as f:
                data = json.load(f)
            return {"count": len(data), "data": data}
        return {"count": 0, "data": []}
    except Exception as e:
        # Don't crash if file read conflicts, just return empty
        return {"count": 0, "data": [], "error": str(e)}
