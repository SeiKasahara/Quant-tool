from fastapi import APIRouter, Response
from app import metrics

router = APIRouter()

@router.get("/metrics")
def metrics_endpoint():
    text = metrics.get_metrics_text()
    return Response(content=text, media_type="text/plain; version=0.0.4")
