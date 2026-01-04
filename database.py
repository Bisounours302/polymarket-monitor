import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use a persistent volume path for Docker, or local for development
DB_PATH = os.getenv("DB_PATH", "sqlite:///alerts.db")

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

def get_engine():
    return create_engine(DB_PATH, echo=False)

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
