import re
from typing import List, Dict, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

class EventExtractor:
    def __init__(self):
        # Define event patterns
        self.event_patterns = {
            "guidance_up": [
                r"raises?\s+(?:full[- ]?year\s+)?guidance",
                r"increases?\s+(?:revenue\s+)?outlook",
                r"upgrades?\s+(?:earnings\s+)?forecast",
                r"boosts?\s+(?:profit\s+)?guidance",
                r"lifts?\s+(?:sales\s+)?expectations"
            ],
            "guidance_down": [
                r"lowers?\s+(?:full[- ]?year\s+)?guidance",
                r"cuts?\s+(?:revenue\s+)?outlook",
                r"reduces?\s+(?:earnings\s+)?forecast",
                r"slashes?\s+(?:profit\s+)?guidance",
                r"downgrades?\s+expectations"
            ],
            "earnings_beat": [
                r"beats?\s+(?:earnings\s+)?estimates?",
                r"tops?\s+(?:profit\s+)?expectations?",
                r"exceeds?\s+(?:revenue\s+)?forecasts?",
                r"surpasses?\s+(?:wall\s+street\s+)?estimates?",
                r"stronger[- ]than[- ]expected\s+(?:earnings|results)"
            ],
            "earnings_miss": [
                r"misses?\s+(?:earnings\s+)?estimates?",
                r"falls?\s+short\s+of\s+expectations?",
                r"disappoints?\s+(?:on\s+)?(?:earnings|revenue)",
                r"below\s+(?:wall\s+street\s+)?estimates?",
                r"weaker[- ]than[- ]expected\s+(?:earnings|results)"
            ],
            "mna": [
                r"acquires?\s+",
                r"to\s+acquire\s+",
                r"merger\s+(?:with|agreement)",
                r"takeover\s+(?:bid|offer)",
                r"agrees?\s+to\s+(?:buy|purchase|merge)",
                r"completes?\s+(?:acquisition|merger)",
                r"announces?\s+(?:acquisition|merger)"
            ],
            "litigation": [
                r"lawsuit\s+(?:filed|against)",
                r"sued\s+(?:by|for)",
                r"legal\s+(?:action|proceedings?)",
                r"regulatory\s+(?:probe|investigation)",
                r"(?:SEC|DOJ|FTC)\s+(?:investigat|prob|inquir)",
                r"settles?\s+(?:lawsuit|charges?)",
                r"class[- ]action\s+(?:lawsuit|suit)"
            ],
            "product_launch": [
                r"launches?\s+(?:new\s+)?product",
                r"unveils?\s+(?:new\s+)?(?:product|service)",
                r"introduces?\s+(?:new\s+)?(?:product|offering)",
                r"debuts?\s+(?:new\s+)?(?:product|platform)",
                r"announces?\s+(?:new\s+)?(?:product|service)\s+launch"
            ],
            "executive_change": [
                r"(?:CEO|CFO|CTO|COO)\s+(?:resigns?|departs?|steps?\s+down)",
                r"appoints?\s+(?:new\s+)?(?:CEO|CFO|CTO|COO)",
                r"names?\s+(?:new\s+)?(?:chief|president)",
                r"(?:executive|leadership)\s+(?:change|transition)",
                r"replaces?\s+(?:CEO|CFO|CTO|COO)"
            ],
            "dividend": [
                r"declares?\s+(?:quarterly\s+)?dividend",
                r"announces?\s+(?:dividend|distribution)",
                r"increases?\s+dividend",
                r"cuts?\s+dividend",
                r"suspends?\s+dividend",
                r"dividend\s+(?:payment|declaration)"
            ],
            "buyback": [
                r"share\s+(?:buyback|repurchase)",
                r"stock\s+(?:buyback|repurchase)",
                r"authorizes?\s+(?:\$[\d.]+[BMK]?\s+)?(?:buyback|repurchase)",
                r"announces?\s+(?:\$[\d.]+[BMK]?\s+)?(?:buyback|repurchase)",
                r"expands?\s+(?:buyback|repurchase)\s+program"
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for event_type, patterns in self.event_patterns.items():
            self.compiled_patterns[event_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def extract_events(self, text: str, document_time: datetime, tickers: List[str] = None) -> List[Dict]:
        events = []
        text_lower = text.lower()
        
        for event_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.finditer(text_lower)
                for match in matches:
                    # Extract context around match
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end]
                    
                    # Try to extract affected ticker from context
                    affected_ticker = self._extract_ticker_from_context(context, tickers)
                    
                    # Calculate confidence based on pattern strength
                    confidence = self._calculate_confidence(event_type, context)
                    
                    event = {
                        "event_type": event_type,
                        "event_time": document_time,
                        "headline": self._generate_headline(event_type, affected_ticker),
                        "confidence_extraction": confidence,
                        "affected_ticker": affected_ticker,
                        "payload": {
                            "matched_text": match.group(0),
                            "context": context,
                            "position": match.start()
                        }
                    }
                    
                    events.append(event)
        
        # Deduplicate similar events
        events = self._deduplicate_events(events)
        
        return events
    
    def _extract_ticker_from_context(self, context: str, known_tickers: List[str] = None) -> Optional[str]:
        if not known_tickers:
            return None
        
        # Look for known tickers in context
        for ticker in known_tickers:
            if ticker in context.upper():
                return ticker
        
        return None
    
    def _calculate_confidence(self, event_type: str, context: str) -> float:
        # Base confidence scores for different event types
        base_confidence = {
            "guidance_up": 0.8,
            "guidance_down": 0.8,
            "earnings_beat": 0.85,
            "earnings_miss": 0.85,
            "mna": 0.9,
            "litigation": 0.75,
            "product_launch": 0.7,
            "executive_change": 0.85,
            "dividend": 0.9,
            "buyback": 0.85
        }
        
        confidence = base_confidence.get(event_type, 0.7)
        
        # Adjust confidence based on context signals
        if any(word in context.lower() for word in ["confirmed", "announced", "reported"]):
            confidence += 0.05
        if any(word in context.lower() for word in ["rumor", "speculation", "possibly", "may"]):
            confidence -= 0.15
        
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_headline(self, event_type: str, ticker: Optional[str] = None) -> str:
        ticker_str = f"{ticker} " if ticker else ""
        
        headlines = {
            "guidance_up": f"{ticker_str}Raises Guidance",
            "guidance_down": f"{ticker_str}Lowers Guidance",
            "earnings_beat": f"{ticker_str}Beats Earnings Estimates",
            "earnings_miss": f"{ticker_str}Misses Earnings Estimates",
            "mna": f"{ticker_str}M&A Activity",
            "litigation": f"{ticker_str}Legal Proceedings",
            "product_launch": f"{ticker_str}Product Launch",
            "executive_change": f"{ticker_str}Executive Change",
            "dividend": f"{ticker_str}Dividend Announcement",
            "buyback": f"{ticker_str}Share Buyback"
        }
        
        return headlines.get(event_type, f"{ticker_str}Corporate Event")
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        # Remove duplicate events of same type within close positions
        unique_events = []
        seen = set()
        
        for event in events:
            key = (
                event["event_type"],
                event.get("affected_ticker"),
                event["payload"]["position"] // 500  # Group by text chunks
            )
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events

# Global instance
event_extractor = EventExtractor()