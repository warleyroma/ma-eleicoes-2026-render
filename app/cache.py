from __future__ import annotations
import time
from threading import Lock

class TTLCache:
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self.data = {}
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            item = self.data.get(key)
            if not item:
                return None
            expires, value = item
            if expires < time.time():
                self.data.pop(key, None)
                return None
            return value

    def set(self, key, value):
        with self.lock:
            self.data[key] = (time.time() + self.ttl, value)
