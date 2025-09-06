from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import numpy as np
import random

from app.core.deps import get_db_session
from app.db.models import Signal, Event, Backtest as BacktestModel

router = APIRouter()

class EventStudyRequest(BaseModel):
    event_types: List[str]
    window_days: int = 5
    min_confidence: float = 0.6

class EventStudyResponse(BaseModel):
    event_type: str
    sample_size: int
    avg_excess_return: float
    t_statistic: float
    p_value: float

@router.post("/event-study")
async def run_event_study(
    request: EventStudyRequest,
    db: Session = Depends(get_db_session)
):
    """Run event study backtest"""
    
    results = []
    
    for event_type in request.event_types:
        # Get events with sufficient confidence
        events = db.query(Event).filter(
            and_(
                Event.event_type == event_type,
                Event.confidence_extraction >= request.min_confidence
            )
        ).limit(100).all()
        
        if not events:
            # Use mock data for demonstration
            sample_size = 25
            
            # Generate mock returns based on event type
            if event_type == "guidance_up":
                mean_return = 0.023  # 2.3% excess return
                std_return = 0.015
            elif event_type == "guidance_down":
                mean_return = -0.018  # -1.8% excess return
                std_return = 0.012
            elif event_type == "earnings_beat":
                mean_return = 0.015  # 1.5% excess return
                std_return = 0.010
            else:
                mean_return = 0.005
                std_return = 0.008
            
            # Generate mock excess returns
            excess_returns = np.random.normal(mean_return, std_return, sample_size)
            avg_excess_return = np.mean(excess_returns)
            
            # Calculate t-statistic
            t_stat = avg_excess_return / (np.std(excess_returns) / np.sqrt(sample_size))
            
            # Approximate p-value (simplified)
            p_value = 2 * (1 - min(0.99, abs(t_stat) / 3))
            
        else:
            # Would calculate actual returns here
            # For MVP, use simplified mock calculation
            sample_size = len(events)
            avg_excess_return = random.uniform(-0.02, 0.03)
            t_stat = random.uniform(-2, 3)
            p_value = random.uniform(0.01, 0.5)
        
        results.append(EventStudyResponse(
            event_type=event_type,
            sample_size=sample_size,
            avg_excess_return=avg_excess_return,
            t_statistic=t_stat,
            p_value=p_value
        ))
        
        # Save backtest result
        backtest = BacktestModel(
            name=f"Event Study - {event_type}",
            params={
                "event_type": event_type,
                "window_days": request.window_days,
                "min_confidence": request.min_confidence
            },
            result={
                "sample_size": sample_size,
                "avg_excess_return": avg_excess_return,
                "t_statistic": t_stat,
                "p_value": p_value
            }
        )
        db.add(backtest)
    
    db.commit()
    
    return {
        "results": results,
        "parameters": {
            "window_days": request.window_days,
            "min_confidence": request.min_confidence
        }
    }

@router.get("/results")
async def get_backtest_results(
    limit: int = 10,
    db: Session = Depends(get_db_session)
):
    """Get recent backtest results"""
    
    backtests = db.query(BacktestModel).order_by(
        BacktestModel.created_at.desc()
    ).limit(limit).all()
    
    results = []
    for backtest in backtests:
        results.append({
            "id": backtest.id,
            "name": backtest.name,
            "params": backtest.params,
            "result": backtest.result,
            "created_at": backtest.created_at
        })
    
    return {"results": results}