"""Forward upstream attlog_*.jsonl files. Read-only input; durable replay cursor.

Run exactly one process per directory. Restart/replay is safe at the backend.
Never point this at OPERLOG files (they may contain biometric templates).
"""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen


def forward(directory: Path, state_path: Path, url: str, token: str):
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for path in sorted(directory.glob('attlog_*.jsonl')):
        stat = path.stat()
        entry = state.get(path.name, {})
        offset = entry.get('offset', 0)
        if entry and (entry.get('inode') != stat.st_ino or stat.st_size < offset):
            raise RuntimeError('Input rotated/truncated: archive retained source and reset checkpoint explicitly')
        with path.open('rb') as source:
            source.seek(offset)
            while True:
                line = source.readline(16385)
                if not line or not line.endswith(b'\n'):
                    if len(line) > 16384:
                        raise RuntimeError('Oversized receiver record; restricted operator inspection required')
                    break  # Partial writes are retried after receiver finishes.
                record = json.loads(line)
                request = Request(url.rstrip('/') + '/internal/face-receiver/records',
                    data=json.dumps(record).encode(), headers={'Content-Type': 'application/json', 'x-face-adapter-token': token})
                with urlopen(request, timeout=30) as response:
                    if response.status != 202:
                        raise RuntimeError('Backend did not durably accept record')
                state[path.name] = {'inode': stat.st_ino, 'offset': source.tell()}
                temporary = state_path.with_suffix('.tmp')
                with temporary.open('w') as output:
                    os.chmod(temporary, 0o600)
                    json.dump(state, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, state_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    token = os.environ['FACE_ADAPTER_TOKEN']
    while True:
        try:
            forward(args.directory, args.state, args.url, token)
        except Exception as exc:
            # Exception details may contain upstream sensitive data: log type only.
            print('Forwarding stopped/retrying:', type(exc).__name__, flush=True)
            if args.once:
                raise SystemExit(1)
        if args.once:
            return
        time.sleep(5)


if __name__ == '__main__':
    main()
