"""Isolated test harness around the inspected community receiver.

Protocol behavior comes from the separately checked out, pinned server.py.
This wrapper adds serial allowlisting, bounded attendance-only ingress and
fsync before the upstream handler can return its successful response.
It does not establish physical-terminal authenticity. Use a private LAN/VPN.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
from urllib.parse import parse_qs

source = Path(os.environ['ADMS_SOURCE_DIR']).resolve() / 'server.py'
if hashlib.sha256(source.read_bytes()).hexdigest() != 'a3149be6b3429fbec6d7b68a3447de59386315ff8691d933c89f9197cb3ece66':
    raise RuntimeError('Receiver source differs from the reviewed revision; review before updating')
allowed = set(os.environ['ADMS_ALLOWED_SERIALS'].split(','))
if not allowed or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', sn) for sn in allowed):
    raise RuntimeError('Configure explicit valid ADMS_ALLOWED_SERIALS')
# Safe explicit directories are required before upstream module import creates them.
for setting in ('ADMS_DATA_DIR', 'ADMS_EVENT_LOG', 'ADMS_CMD_QUEUE'):
    if not os.environ.get(setting):
        raise RuntimeError(f'{setting} must be configured')
spec = importlib.util.spec_from_file_location('schoolbus_upstream_adms', source)
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)
original_save = upstream._save_attlog


def durable_save(sn, lines):
    original_save(sn, lines)
    with (upstream.DATA_DIR / f'attlog_{sn}.jsonl').open('rb') as saved:
        os.fsync(saved.fileno())
    directory_fd = os.open(upstream.DATA_DIR, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


upstream._save_attlog = durable_save
# Upstream's global command queue is not serial scoped. No commands are permitted.
upstream._pop_command = lambda: None


class AttendanceOnlyIngress:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] == '/health':
            return await self.wrapped(scope, receive, send)
        params = parse_qs(scope.get('query_string', b'').decode('ascii', errors='replace'))
        async def reject(status):
            await send({'type': 'http.response.start', 'status': status, 'headers': []})
            await send({'type': 'http.response.body', 'body': b''})
        serials = params.get('SN', [])
        if len(serials) != 1 or serials[0] not in allowed:
            return await reject(403)
        if scope['method'] == 'POST':
            if scope['path'] != '/iclock/cdata.aspx' or params.get('table') != ['ATTLOG']:
                return await reject(403)
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > 1024 * 1024:
                    return await reject(413)
                if not message.get('more_body', False):
                    break
            try:
                lines = [line for line in body.decode('utf-8').splitlines() if line.strip()]
            except UnicodeError:
                return await reject(422)
            records = [line for line in lines if not line.startswith('SN=')]
            if not records or any('\t' not in line or len(line) > 4096 for line in records):
                return await reject(422)
            async def replay():
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await self.wrapped(scope, replay, send)
        return await self.wrapped(scope, receive, send)


app = AttendanceOnlyIngress(upstream.app)
