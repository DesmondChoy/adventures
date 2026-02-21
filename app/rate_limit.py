"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage is fine for single-dyno deployment
limiter = Limiter(key_func=get_remote_address)
