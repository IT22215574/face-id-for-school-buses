#!/bin/bash
# Build a physical-device APK against a verified public HTTPS backend.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -ne 1 ]; then
  echo "Usage: bash scripts/build-internet-apk.sh https://YOUR-DOMAIN.ngrok-free.app" >&2
  exit 1
fi
API_TEST_URL="${1%/}"
python3 - "$API_TEST_URL" <<'PY'
import json
import sys
import urllib.request
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)
if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
        parsed.password or parsed.query or parsed.fragment or parsed.path):
    sys.exit('Use the public HTTPS origin only, without a path or credentials.')
request = urllib.request.Request(url + '/health', headers={
    'ngrok-skip-browser-warning': 'true',
    'Accept': 'application/json',
})
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        health = json.load(response)
    if health.get('status') != 'ok':
        sys.exit('Backend health check failed.')
except Exception as exc:
    sys.exit(f'Cannot reach the public backend: {exc}')
print('Public backend health check passed.')
PY
cd flutter_app
flutter build apk --release --dart-define="API_BASE_URL=$API_TEST_URL"
echo "Install flutter_app/build/app/outputs/flutter-apk/app-release.apk on each Android tester's phone."
