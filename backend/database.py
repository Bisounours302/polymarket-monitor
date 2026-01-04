import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use a persistent volume path for Docker, or local for development
# Use a persistent volume path for Docker, or local for development
DB_PATH = os.getenv("DB_PATH", "sqlite:///alerts.db")

# Ensure directory exists if DB_PATH is a file path
if "sqlite:///" in DB_PATH:
    path = DB_PATH.replace("sqlite:///", "")
    # Handle absolute paths correctly in Docker (starts with /)
    if not path.startswith("/"):
        path = os.path.abspath(path)
    
    os.makedirs(os.path.dirname(path), exist_ok=True)

Base = declarative_base()

class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    market_name = Column(String(255))
    amount_usd = Column(Float)
    wallet_address = Column(String(42))
    nonce = Column(Integer)
    polymarket_url = Column(Text)
    tx_hash = Column(String(66), nullable=True)

    def __repr__(self):
        return f"<Alert(wallet='{self.wallet_address}', amount={self.amount_usd}, nonce={self.nonce})>"

class GlobalSettings(Base):
    __tablename__ = 'settings'
    
    key = Column(String(50), primary_key=True)
    value = Column(String(255)) # Store as string, parse as needed (e.g., "true"/"false")

def get_engine():
    return create_engine(DB_PATH, echo=False)

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Seed default settings
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        defaults = {
            "notify_whales": "true",
            "notify_suspicious": "true"
        }
        for k, v in defaults.items():
            if not session.query(GlobalSettings).filter_by(key=k).first():
                session.add(GlobalSettings(key=k, value=v))
        session.commit()
    except Exception as e:
        print(f"Error seeding settings: {e}")
    finally:
        session.close()

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
