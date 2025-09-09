import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
import structlog

from app.core.config import settings
from app.core.calibrator import calibrator

logger = structlog.get_logger()

class SignalFuser:
    def __init__(self):
        # Load weights from config
        self.w_src = settings.W_SRC
        self.w_novel = settings.W_NOVEL
        self.w_evt = settings.W_EVT
        self.w_buzz = settings.W_BUZZ
        self.k_cons = settings.K_CONS
        self.k_unc = settings.K_UNC
        self.tau = settings.TAU
        
    # Source weights mapping (can be reloaded at runtime)
        self.source_weights = {
            "dj": 0.9,           # Dow Jones
            "nasdaq": 0.85,      # NASDAQ
            "reuters": 0.9,      # Reuters
            "bloomberg": 0.95,   # Bloomberg
            "wsj": 0.9,         # Wall Street Journal
            "default": 0.5      # Unknown sources
        }
        
        # Event prior probabilities (can be reloaded at runtime)
        self.event_priors = {
            "guidance_up": 0.8,
            "guidance_down": 0.85,
            "earnings_beat": 0.75,
            "earnings_miss": 0.8,
            "mna": 0.9,
            "litigation": 0.6,
            "product_launch": 0.65,
            "executive_change": 0.7,
            "dividend": 0.85,
            "buyback": 0.8,
            "default": 0.5
        }
        # Attempt to load persisted settings file (if present)
        try:
            from pathlib import Path
            cfg_path = Path(__file__).resolve().parents[1] / 'configs' / 'fuser_settings.json'
            self.reload_from_file(cfg_path)
        except Exception:
            pass

    def reload_from_dict(self, data: dict):
        """Apply settings from a dict (weights, source_weights, event_priors)"""
        w = data.get('weights', {})
        # update scalar weights if present
        self.w_src = float(w.get('W_SRC', self.w_src))
        self.w_novel = float(w.get('W_NOVEL', self.w_novel))
        self.w_evt = float(w.get('W_EVT', self.w_evt))
        self.w_buzz = float(w.get('W_BUZZ', self.w_buzz))
        self.k_cons = float(w.get('K_CONS', self.k_cons))
        self.k_unc = float(w.get('K_UNC', self.k_unc))
        self.tau = float(w.get('TAU', self.tau))

        # update dicts
        if 'source_weights' in data and isinstance(data['source_weights'], dict):
            self.source_weights.update({k: float(v) for k, v in data['source_weights'].items()})

        if 'event_priors' in data and isinstance(data['event_priors'], dict):
            self.event_priors.update({k: float(v) for k, v in data['event_priors'].items()})

    def save_to_file(self, path):
        import json
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'weights': {
                'W_SRC': self.w_src,
                'W_NOVEL': self.w_novel,
                'W_EVT': self.w_evt,
                'W_BUZZ': self.w_buzz,
                'K_CONS': self.k_cons,
                'K_UNC': self.k_unc,
                'TAU': self.tau
            },
            'source_weights': self.source_weights,
            'event_priors': self.event_priors
        }
        p.write_text(json.dumps(data, indent=2))

    def reload_from_file(self, path):
        import json
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            self.reload_from_dict(data)
        except Exception:
            # ignore parse errors
            return
    
    def calculate_confidence(
        self,
        source: str,
        novelty: float,
        event_type: Optional[str],
        buzz_score: float,
        insider_contra: int = 0,
        model_uncertainty: float = 0.0,
        signal_time: datetime = None,
        current_time: datetime = None
    ) -> Tuple[float, float, Dict]:
        """
        Calculate signal confidence score
        Returns: (confidence, base_score, components_dict)
        """
        
        # Get source weight
        source_key = source.lower() if source else "default"
        src_weight = self.source_weights.get(source_key, self.source_weights["default"])
        
        # Get event prior
        evt_prior = self.event_priors.get(event_type, self.event_priors["default"])
        
        # Apply sigmoid to buzz score
        buzz_score_normalized = self._sigmoid(buzz_score)
        
        # Calculate base score
        base_score = (
            self.w_src * src_weight +
            self.w_novel * novelty +
            self.w_evt * evt_prior +
            self.w_buzz * buzz_score_normalized
        )
        
        # Consistency adjustment
        consistency_adj = self.k_cons * insider_contra
        
        # Uncertainty adjustment
        uncertainty_adj = -self.k_unc * model_uncertainty
        
        # Time decay
        time_decay = 1.0
        if signal_time and current_time:
            delta_t = (current_time - signal_time).total_seconds()
            time_decay = math.exp(-delta_t / self.tau)
        
        # Calculate raw score
        raw_score = (base_score + consistency_adj + uncertainty_adj) * time_decay
        raw_score = max(0.0, min(1.0, raw_score))  # Clip to [0, 1]
        
        # Apply calibration
        confidence = calibrator.transform(raw_score)
        
        # Build components dictionary for transparency
        components = {
            "source_weight": src_weight,
            "novelty": novelty,
            "event_prior": evt_prior,
            "buzz_score": buzz_score_normalized,
            "base_score": base_score,
            "consistency_adj": consistency_adj,
            "uncertainty_adj": uncertainty_adj,
            "time_decay": time_decay,
            "raw_score": raw_score,
            "weights": {
                "w_src": self.w_src,
                "w_novel": self.w_novel,
                "w_evt": self.w_evt,
                "w_buzz": self.w_buzz
            }
        }
        
        logger.info(
            "Calculated signal confidence",
            confidence=confidence,
            base_score=base_score,
            source=source,
            event_type=event_type
        )
        
        return confidence, base_score, components
    
    def _sigmoid(self, x: float, a: float = 1.0) -> float:
        """Sigmoid function for normalizing scores"""
        return 1 / (1 + math.exp(-a * x))
    
    def determine_signal_direction(
        self,
        event_type: str,
        sentiment: str,
        sentiment_score: float
    ) -> str:
        """Determine signal direction based on event and sentiment"""
        
        # Event-based direction
        bullish_events = {
            "guidance_up", "earnings_beat", "product_launch", 
            "buyback", "dividend"
        }
        bearish_events = {
            "guidance_down", "earnings_miss", "litigation"
        }
        
        if event_type in bullish_events:
            base_direction = "up"
        elif event_type in bearish_events:
            base_direction = "down"
        else:
            base_direction = "neutral"
        
        # Adjust based on sentiment if strong enough
        if sentiment_score > 0.8:
            if sentiment == "positive" and base_direction != "down":
                return "up"
            elif sentiment == "negative" and base_direction != "up":
                return "down"
        
        return base_direction
    
    def generate_signal_label(
        self,
        event_type: str,
        sentiment: str,
        confidence: float
    ) -> str:
        """Generate human-readable signal label"""
        
        event_labels = {
            "guidance_up": "Guidance Raised",
            "guidance_down": "Guidance Lowered",
            "earnings_beat": "Earnings Beat",
            "earnings_miss": "Earnings Miss",
            "mna": "M&A Activity",
            "litigation": "Legal Risk",
            "product_launch": "Product Launch",
            "executive_change": "Leadership Change",
            "dividend": "Dividend Update",
            "buyback": "Share Buyback"
        }
        
        base_label = event_labels.get(event_type, "Market Event")
        
        # Add confidence qualifier
        if confidence >= 0.8:
            qualifier = "High Confidence"
        elif confidence >= 0.6:
            qualifier = "Moderate Confidence"
        else:
            qualifier = "Low Confidence"
        
        return f"{base_label} ({qualifier})"
    
    def should_alert(
        self,
        confidence: float,
        source_weight: float,
        novelty: float,
        has_second_source: bool
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if signal should trigger alert
        Returns: (should_alert, reason)
        """
        
        # High priority conditions
        if source_weight >= settings.HIGH_PRIORITY_SOURCE_WEIGHT:
            return True, "High-priority source"
        
        if novelty >= settings.HIGH_NOVELTY_THRESHOLD:
            return True, "High novelty score"
        
        # Standard threshold
        if confidence >= settings.MIN_CONFIDENCE_DEFAULT:
            if not has_second_source:
                return True, "Needs second source confirmation"
            return True, "Confidence threshold met"
        
        return False, None

# Global instance
signal_fuser = SignalFuser()