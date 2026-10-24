"""Synthetic spool tests; no device data or network calls."""
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('face_forwarder', Path(__file__).parents[1] / 'scripts/forward_adms.py')
forwarder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forwarder)


def test_cursor_advances_only_after_durable_acceptance(tmp_path, monkeypatch):
    line = json.dumps({'sn': 'SYNTHETIC', 'raw': 'synthetic-test-only'}) + '\n'
    spool = tmp_path / 'attlog_SYNTHETIC.jsonl'; spool.write_text(line)
    state = tmp_path / 'cursor.json'
    sent = []
    def unavailable(*args, **kwargs): raise OSError('Synthetic outage')
    monkeypatch.setattr(forwarder, 'urlopen', unavailable)
    with pytest.raises(OSError): forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
    assert not state.exists()
    class Accepted:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def accept(request, timeout):
        sent.append(json.loads(request.data)); return Accepted()
    monkeypatch.setattr(forwarder, 'urlopen', accept)
    forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
    assert json.loads(state.read_text())[spool.name]['offset'] == len(line.encode())
    forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
    assert len(sent) == 1
    spool.write_text(line + line[:-1])
    forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
    assert len(sent) == 1
    with spool.open('a') as file: file.write('\n')
    forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
    assert len(sent) == 2
    spool.write_text('')
    with pytest.raises(RuntimeError): forwarder.forward(tmp_path, state, 'http://localhost', 'test-token')
