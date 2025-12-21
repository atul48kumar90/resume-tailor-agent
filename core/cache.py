import json
import hashlib
import redis
import os

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def get_cached_jd(jd_text: str):
    key = f"jd:{_hash(jd_text)}"
    data = redis_client.get(key)
    return json.loads(data) if data else None


def set_cached_jd(jd_text: str, value: dict, ttl=3600):
    key = f"jd:{_hash(jd_text)}"
    redis_client.setex(key, ttl, json.dumps(value))
