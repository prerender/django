"""Shared pytest fixtures for django integration tests.

The `mock_server` fixture spawns the prerender integration-contract mock
server (a Node script) for the duration of the test session. CI fetches
mock-server.mjs into the repo root before running tests; locally:

    curl -fsSL -o mock-server.mjs https://raw.githubusercontent.com/prerender/integration-contract/main/mock-server.mjs
"""

import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

MOCK_SERVER_PATH = Path(os.environ.get(
    'MOCK_SERVER_PATH',
    Path(__file__).parent.parent / 'mock-server.mjs',
))


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_for_health(url, attempts=50, delay=0.1):
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(delay)
    raise RuntimeError(f'mock server at {url} did not become ready')


@pytest.fixture(scope='session')
def mock_server():
    if not MOCK_SERVER_PATH.exists():
        pytest.skip(
            f'mock-server.mjs not found at {MOCK_SERVER_PATH}; fetch it via '
            'curl -fsSL -o mock-server.mjs '
            'https://raw.githubusercontent.com/prerender/integration-contract/main/mock-server.mjs'
        )

    port = _free_port()
    proc = subprocess.Popen(
        ['node', str(MOCK_SERVER_PATH)],
        env={**os.environ, 'PORT': str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    url = f'http://127.0.0.1:{port}'
    try:
        _wait_for_health(f'{url}/__health')
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(autouse=True)
def reset_mock(mock_server):
    req = urllib.request.Request(f'{mock_server}/__reset', method='POST')
    urllib.request.urlopen(req).read()
    yield


def get_recorded(mock_server):
    with urllib.request.urlopen(f'{mock_server}/__requests') as resp:
        import json
        return json.loads(resp.read())
