import httpx
import json
from typing import Dict, Optional, List
from datetime import datetime
import structlog

from app.core.config import settings

logger = structlog.get_logger()

class SlackNotifier:
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK
        self.is_configured = bool(self.webhook_url and 
                                 self.webhook_url != "https://hooks.slack.com/services/xxx/yyy/zzz")
    
    async def send_signal_alert(
        self,
        ticker: str,
        signal_label: str,
        confidence: float,
        direction: str,
        sources: List[Dict],
        signal_time: datetime,
        evidence: Optional[Dict] = None
    ) -> bool:
        """Send signal alert to Slack"""
        
        if not self.is_configured:
            logger.info(
                "Slack notification DRY-RUN (no webhook configured)",
                ticker=ticker,
                signal_label=signal_label,
                confidence=confidence
            )
            return True
        
        # Build Slack message
        message = self._build_slack_message(
            ticker, signal_label, confidence, direction,
            sources, signal_time, evidence
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(
                        "Slack notification sent successfully",
                        ticker=ticker,
                        signal_label=signal_label
                    )
                    return True
                else:
                    logger.error(
                        "Failed to send Slack notification",
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error sending Slack notification",
                error=str(e),
                ticker=ticker
            )
            return False
    
    def _build_slack_message(
        self,
        ticker: str,
        signal_label: str,
        confidence: float,
        direction: str,
        sources: List[Dict],
        signal_time: datetime,
        evidence: Optional[Dict] = None
    ) -> Dict:
        """Build Slack message with rich formatting"""
        
        # Direction emoji
        direction_emoji = {
            "up": "📈",
            "down": "📉",
            "neutral": "➡️"
        }.get(direction, "❓")
        
        # Confidence color
        if confidence >= 0.8:
            color = "good"  # Green
        elif confidence >= 0.6:
            color = "warning"  # Yellow
        else:
            color = "danger"  # Red
        
        # Build source list
        source_text = "\n".join([f"• {s.get('title', 'Unknown')}" for s in sources[:3]])
        if len(sources) > 3:
            source_text += f"\n• ... and {len(sources) - 3} more"
        
        # Build message
        message = {
            "text": f"{direction_emoji} Signal Alert: {ticker}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Ticker",
                            "value": ticker,
                            "short": True
                        },
                        {
                            "title": "Signal",
                            "value": signal_label,
                            "short": True
                        },
                        {
                            "title": "Confidence",
                            "value": f"{confidence:.1%}",
                            "short": True
                        },
                        {
                            "title": "Direction",
                            "value": direction.capitalize(),
                            "short": True
                        },
                        {
                            "title": "Sources",
                            "value": source_text,
                            "short": False
                        }
                    ],
                    "footer": "Signal Detection System",
                    "ts": int(signal_time.timestamp())
                }
            ]
        }
        
        # Add evidence if provided
        if evidence:
            evidence_fields = []
            
            if "novelty" in evidence:
                evidence_fields.append({
                    "title": "Novelty Score",
                    "value": f"{evidence['novelty']:.2f}",
                    "short": True
                })
            
            if "event_type" in evidence:
                evidence_fields.append({
                    "title": "Event Type",
                    "value": evidence["event_type"],
                    "short": True
                })
            
            if evidence_fields:
                message["attachments"].append({
                    "color": "#36a64f",
                    "title": "Signal Evidence",
                    "fields": evidence_fields
                })
        
        return message
    
    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None
    ) -> bool:
        """Send error notification to Slack"""
        
        if not self.is_configured:
            logger.info(
                "Slack error notification DRY-RUN",
                error_type=error_type,
                error_message=error_message
            )
            return True
        
        message = {
            "text": f"⚠️ System Error: {error_type}",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {
                            "title": "Error Type",
                            "value": error_type,
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": error_message,
                            "short": False
                        }
                    ],
                    "footer": "Signal Detection System",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }
        
        if context:
            context_str = json.dumps(context, indent=2)[:500]
            message["attachments"][0]["fields"].append({
                "title": "Context",
                "value": f"```{context_str}```",
                "short": False
            })
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=message,
                    timeout=10.0
                )
                return response.status_code == 200
        except:
            return False

# Global instance
slack_notifier = SlackNotifier()