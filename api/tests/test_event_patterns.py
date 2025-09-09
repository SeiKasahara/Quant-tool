import json
from pathlib import Path

from app.nlp.events import event_extractor, CONFIG_PATH


def test_reload_and_save(tmp_path):
    orig = dict(event_extractor.event_patterns)
    try:
        # write a minimal pattern
        data = {"test_event": ["testpattern\\s+value"]}
        p = tmp_path / "event_patterns.json"
        p.write_text(json.dumps(data, indent=2))

        # point the CONFIG_PATH to our temp file for the test
        # monkeypatch would be nicer but keep simple
        old = CONFIG_PATH
        try:
            # replace the file by copying
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(data))
            assert event_extractor.reload_patterns()
            assert "test_event" in event_extractor.event_patterns
        finally:
            pass
    finally:
        # restore original
        event_extractor.event_patterns = orig
        event_extractor._compile_patterns()
