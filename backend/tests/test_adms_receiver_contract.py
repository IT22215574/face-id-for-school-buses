"""Opt-in actual upstream-source contract test, using SYNTHETIC attendance only.

ADMS_TEST_SOURCE_DIR must point to the separately pinned public checkout.
This verifies source integration; it is not a physical-device compatibility test.
"""
import importlib.util
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient
import pytest


def test_upstream_source_wrapper_and_durable_ack(tmp_path, monkeypatch):
    source = os.getenv('ADMS_TEST_SOURCE_DIR')
    if not source:
        pytest.skip('Set ADMS_TEST_SOURCE_DIR to the pinned reviewed receiver checkout')
    for key, value in {'ADMS_SOURCE_DIR': source, 'ADMS_ALLOWED_SERIALS': 'SYNTHETIC-TEST',
                       'ADMS_DATA_DIR': str(tmp_path / 'data'), 'ADMS_EVENT_LOG': str(tmp_path / 'events.jsonl'),
                       'ADMS_CMD_QUEUE': str(tmp_path / 'commands.jsonl')}.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location('isolated_receiver_test', Path(__file__).parents[1] / 'integrations/adms_receiver.py')
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    url = '/iclock/cdata.aspx?SN=SYNTHETIC-TEST&table=ATTLOG'
    raw = '1001\t2026-10-20 07:30:00\t0\t15\t0'
    with TestClient(wrapper.app, raise_server_exceptions=False) as client:
        assert client.post(url.replace('SYNTHETIC-TEST', 'UNKNOWN'), content=raw).status_code == 403
        assert client.post(url.replace('ATTLOG', 'OPERLOG'), content='synthetic').status_code == 403
        assert client.post(url, content='not a receiver row').status_code == 422
        assert client.post(url, content=b'\xff\t').status_code == 422
        assert client.post(url, content=b'x' * (1024 * 1024 + 1)).status_code == 413
        assert client.post(url, content=raw).text == 'OK: 1'
        saved = json.loads((tmp_path / 'data/attlog_SYNTHETIC-TEST.jsonl').read_text())
        assert set(saved) == {'ts', 'sn', 'pin', 'time', 'status', 'verify', 'raw'}
        assert saved['raw'] == raw and saved['pin'] == '1001'
        (tmp_path / 'commands.jsonl').write_text('{"id":"SYNTHETIC","cmd":"NOT A REAL COMMAND"}\n')
        assert client.get('/iclock/getrequest.aspx?SN=SYNTHETIC-TEST').text == 'OK'
        def fail(fd): raise OSError('Synthetic disk failure')
        monkeypatch.setattr(wrapper.os, 'fsync', fail)
        assert client.post(url, content=raw).status_code == 500
