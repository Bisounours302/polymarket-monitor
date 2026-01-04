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

# Dependency
def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "running", "service": "Polymarket Monitor API"}

@app.get("/alerts", response_model=List[AlertSchema])
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    """Get latest alerts."""
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).limit(limit).all()
    return alerts

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get dashboard stats."""
    total_alerts = db.query(Alert).count()
    # Simple volume sum (if amount_usd is reliable)
    # Using SQL func usually better but python sum is okay for small db
    all_alerts = db.query(Alert).all()
    total_volume = sum([a.amount_usd for a in all_alerts])
    
    max_trade = 0
    if all_alerts:
        max_trade = max([a.amount_usd for a in all_alerts])
        
    return {
        "total_alerts": total_alerts,
        "total_volume": total_volume,
        "max_trade": max_trade
    }

@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get current notification settings."""
    whales = db.query(GlobalSettings).filter_by(key="notify_whales").first()
    suspicious = db.query(GlobalSettings).filter_by(key="notify_suspicious").first()
    
    return {
        "notify_whales": whales.value.lower() == "true" if whales else True,
        "notify_suspicious": suspicious.value.lower() == "true" if suspicious else True
    }

@app.post("/settings")
def update_settings(settings: SettingsSchema, db: Session = Depends(get_db)):
    """Update notification settings."""
    # Update Whales
    whales = db.query(GlobalSettings).filter_by(key="notify_whales").first()
    if not whales:
        whales = GlobalSettings(key="notify_whales", value="true")
        db.add(whales)
    whales.value = str(settings.notify_whales).lower()
    
    # Update Suspicious
    suspicious = db.query(GlobalSettings).filter_by(key="notify_suspicious").first()
    if not suspicious:
        suspicious = GlobalSettings(key="notify_suspicious", value="true")
        db.add(suspicious)
    suspicious.value = str(settings.notify_suspicious).lower()
    
    db.commit()
    return {"status": "updated", "settings": settings}
