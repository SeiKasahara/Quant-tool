from typing import Dict, Tuple
import threading

# Simple in-memory metrics registry for MVP (Prometheus text exposition)
_metrics_lock = threading.Lock()
_counters: Dict[Tuple[str, Tuple[Tuple[str,str], ...]], int] = {}

def _labels_key(labels: Dict[str,str]) -> Tuple[Tuple[str,str], ...]:
    if not labels:
        return tuple()
    return tuple(sorted([(k,str(v)) for k,v in labels.items()]))

def inc_counter(name: str, labels: Dict[str,str]=None, amount: int=1):
    key = (name, _labels_key(labels or {}))
    with _metrics_lock:
        _counters[key] = _counters.get(key, 0) + amount

def get_metrics_text() -> str:
    # Render counters in Prometheus exposition format
    lines = []
    with _metrics_lock:
        for (name, labels), val in _counters.items():
            if labels:
                lbls = ",".join([f'{k}="{v}"' for k,v in labels])
                lines.append(f"{name}{{{lbls}}} {val}")
            else:
                lines.append(f"{name} {val}")
    return "\n".join(lines) + "\n"
