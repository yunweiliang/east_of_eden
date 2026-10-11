"""Lock portfolio/home.html with the site passcode and publish it to the portfolio repo.

The encryption must match the gate in the portfolio's index.html (and its tools/lock.html):
passcode trimmed and lowercased, PBKDF2-SHA-256 with 600,000 iterations into an AES-256-GCM key.
The passcode is only ever held in memory; it is never written to disk or printed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERATIONS = 600_000
PLACEHOLDER = "[Your reflection goes here.]"


def normalize(passcode: str) -> str:
    # Must match normalize() in the gate: passcode.trim().toLowerCase().
    return passcode.strip().lower()


def derive_key(passcode: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", normalize(passcode).encode(), salt, iterations, dklen=32)


def lock(page: str, passcode: str, salt: bytes | None = None, iv: bytes | None = None) -> dict:
    """Encrypt the page into the lock.json format the gate reads."""
    salt = salt or os.urandom(16)
    iv = iv or os.urandom(12)
    ct = AESGCM(derive_key(passcode, salt)).encrypt(iv, page.encode(), None)  # ciphertext + 16-byte tag, as WebCrypto
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iterations": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def unlock(lock_data: dict, passcode: str) -> str:
    """What the gate does in the browser. Raises if the passcode is wrong."""
    raw = lambda k: base64.b64decode(lock_data[k])
    key = derive_key(passcode, raw("salt"), lock_data["iterations"])
    return AESGCM(key).decrypt(raw("iv"), raw("ct"), None).decode()


def lock_json(lock_data: dict) -> str:
    # Same layout as tools/lock.html writes, so diffs between the two stay small.
    return json.dumps(lock_data, indent=2) + "\n"


def git(site: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(site), *args], check=True)
