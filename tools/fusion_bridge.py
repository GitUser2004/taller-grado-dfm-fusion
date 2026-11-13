"""Client for the ClaudeBridge add-in.

Usage:
    python tools/fusion_bridge.py path/to/script.py [--timeout 60]
    python tools/fusion_bridge.py -c "result = design.rootComponent.name"
    python tools/fusion_bridge.py --status

Writes the code to Documents/ClaudeBridge/inbox, waits for the matching
outbox JSON and prints it. Exit code 0 if the code ran without errors.
"""

import argparse
import json
import os
import sys
import time
import uuid

ROOT = os.path.join(os.path.expanduser('~'), 'Documents', 'ClaudeBridge')
INBOX = os.path.join(ROOT, 'inbox')
OUTBOX = os.path.join(ROOT, 'outbox')


def send(code, timeout=60.0):
    os.makedirs(INBOX, exist_ok=True)
    job_id = time.strftime('%Y%m%d_%H%M%S_') + uuid.uuid4().hex[:6]
    tmp = os.path.join(INBOX, job_id + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(code)
    os.replace(tmp, os.path.join(INBOX, job_id + '.py'))  # atomic: never read half-written

    out_path = os.path.join(OUTBOX, job_id + '.json')
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(out_path):
            with open(out_path, encoding='utf-8') as f:
                return json.load(f)
        time.sleep(0.1)
    return {'id': job_id, 'ok': False,
            'error': 'Timeout after {}s. Is Fusion open and ClaudeBridge running?'.format(timeout)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script', nargs='?')
    ap.add_argument('-c', '--code')
    ap.add_argument('--timeout', type=float, default=60)
    ap.add_argument('--status', action='store_true')
    args = ap.parse_args()

    if args.status:
        try:
            with open(os.path.join(ROOT, 'status.json'), encoding='utf-8') as f:
                print(f.read())
        except FileNotFoundError:
            print('{"running": false, "note": "bridge never started"}')
        return 0

    if args.code:
        code = args.code
    elif args.script:
        with open(args.script, encoding='utf-8-sig') as f:  # tolerate BOM
            code = f.read()
    else:
        ap.error('give a script path or -c CODE')

    out = send(code, args.timeout)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
