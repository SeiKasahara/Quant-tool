from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.core.deps import get_db_session
from app.db.models import Ticker, Signal, SignalEvidence, Document, Price

router = APIRouter()

class TickerSignal(BaseModel):
    id: int
    signal_time: datetime
    confidence: float
    label: str
    direction: str
    base_score: float

class PricePoint(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

@router.get("/{symbol}/signals")
async def get_ticker_signals(
    symbol: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
    db: Session = Depends(get_db_session)
):
    """Get signals for a specific ticker"""
    
    # Get ticker
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
    
    # Build query
    query = db.query(Signal).filter(Signal.ticker_id == ticker.id)
    
    # Apply date filters
    if date_from:
        query = query.filter(Signal.signal_time >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.filter(Signal.signal_time <= datetime.combine(date_to, datetime.max.time()))
    
    # Order by signal time descending
    query = query.order_by(Signal.signal_time.desc())
    
    # Apply limit
    signals = query.limit(limit).all()
    
    # Format response
    signal_list = []
    for signal in signals:
        signal_list.append(TickerSignal(
            id=signal.id,
            signal_time=signal.signal_time,
            confidence=signal.confidence,
            label=signal.label,
            direction=signal.direction,
            base_score=signal.base_score
        ))
    
    return {
        "ticker": symbol.upper(),
        "company": ticker.company.name if ticker.company else None,
        "signals": signal_list,
        "total": len(signal_list)
    }

@router.get("/{symbol}/prices")
async def get_ticker_prices(
    symbol: str,
    days: int = 20,
    db: Session = Depends(get_db_session)
):
    """Get price data for ticker (mock data for MVP)"""
    
    # Get ticker
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
    
    # Try to get real prices
    start_date = datetime.now() - timedelta(days=days)
    prices = db.query(Price).filter(
        and_(
            Price.ticker_id == ticker.id,
            Price.ts >= start_date
        )
    ).order_by(Price.ts.desc()).limit(days).all()
    
    if prices:
        # Return real prices
        price_list = []
        for price in reversed(prices):  # Reverse to get chronological order
            price_list.append(PricePoint(
                ts=price.ts,
                open=float(price.open),
                high=float(price.high),
                low=float(price.low),
                close=float(price.close),
                volume=price.volume
            ))
    else:
        # Generate mock prices for demonstration
        import random
        base_price = 100.0
        price_list = []
        
        for i in range(days):
            ts = datetime.now() - timedelta(days=days-i)
            
            # Random walk
            change = random.uniform(-0.03, 0.03)
            base_price *= (1 + change)
            
            open_price = base_price * random.uniform(0.98, 1.02)
            close_price = base_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 1.0)
            
            price_list.append(PricePoint(
                ts=ts,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=random.randint(1000000, 10000000)
            ))
    
    return {
        "ticker": symbol.upper(),
        "prices": price_list,
        "is_mock": len(prices) == 0
    }

@router.get("/{symbol}")
async def get_ticker_info(
    symbol: str,
    db: Session = Depends(get_db_session)
):
    """Get ticker information"""
    
    ticker = db.query(Ticker).options(
        joinedload(Ticker.company)
    ).filter(Ticker.symbol == symbol.upper()).first()
    
    if not ticker:
        raise HTTPException(status_code=404, detail=f"Ticker {symbol} not found")
    
    # Get recent signal count
    recent_signals = db.query(Signal).filter(
        and_(
            Signal.ticker_id == ticker.id,
            Signal.signal_time >= datetime.now() - timedelta(days=7)
        )
    ).count()
    
    return {
        "id": ticker.id,
        "symbol": ticker.symbol,
        "exchange": ticker.exchange,
        "is_active": ticker.is_active,
        "company": {
            "id": ticker.company.id,
            "name": ticker.company.name,
            "sector": ticker.company.sector,
            "industry": ticker.company.industry,
            "market_cap": float(ticker.company.market_cap) if ticker.company.market_cap else None
        } if ticker.company else None,
        "recent_signals": recent_signals
    }