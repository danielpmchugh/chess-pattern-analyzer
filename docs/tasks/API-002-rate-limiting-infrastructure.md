# Task: API-002 - Rate Limiting Infrastructure

**Status**: `todo`
**Priority**: Critical
**Assigned Agent**: backend-developer
**Estimated Effort**: 1-2 days
**Dependencies**: None (can run parallel with API-001)

## Objective

Implement a tiered rate limiting system using Azure Cache for Redis to track API usage by IP address and optional session identifiers, supporting anonymous and future authenticated tiers.

## Success Criteria

1. Enforce rate limits: 20 analyses/day (anonymous), 100/day (future free tier), 1000/day (future pro)
2. Track usage by IP address with cookie/localStorage enhancement
3. Return proper rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
4. Gracefully handle rate limit exceeded scenarios with user-friendly messages
5. Support Redis connection failures with fallback to in-memory limiting
6. Sub-second response time for rate limit checks

## Technical Approach

### 1. Redis Configuration for Azure

```python
from redis import asyncio as aioredis
from typing import Optional
import os

class RedisConfig:
    def __init__(self):
        self.redis_url = os.getenv('AZURE_REDIS_CONNECTION_STRING')
        self.ssl_enabled = True
        self.decode_responses = True
        self.max_connections = 50

    async def get_client(self) -> aioredis.Redis:
        return await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            ssl=self.ssl_enabled,
            ssl_cert_reqs="required",
            max_connections=self.max_connections
        )
```

### 2. Rate Limiter Implementation

```python
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
import hashlib
import json

class TieredRateLimiter:
    TIERS = {
        'anonymous': {'daily': 20, 'hourly': 5},
        'free': {'daily': 100, 'hourly': 20},
        'pro': {'daily': 1000, 'hourly': 100}
    }

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis = redis_client
        self.fallback_limiter = InMemoryRateLimiter() if not redis_client else None

    def get_client_id(self, request: Request) -> str:
        """Generate unique client identifier"""
        # Primary: Use session cookie if available
        session_id = request.cookies.get('session_id')
        if session_id:
            return f"session:{session_id}"

        # Fallback: Use IP + User-Agent fingerprint
        client_ip = request.client.host
        user_agent = request.headers.get('User-Agent', '')
        fingerprint = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()
        return f"ip:{fingerprint}"

    async def check_rate_limit(self, request: Request, tier: str = 'anonymous') -> dict:
        """Check if request is within rate limits"""
        client_id = self.get_client_id(request)
        limits = self.TIERS[tier]

        # Use Redis if available, fallback to in-memory
        limiter = self.redis if self.redis else self.fallback_limiter

        # Check daily limit
        daily_key = f"rate_limit:daily:{client_id}:{datetime.now().date()}"
        daily_count = await self.increment_counter(limiter, daily_key, 86400)

        # Check hourly limit
        hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        hourly_key = f"rate_limit:hourly:{client_id}:{hour.isoformat()}"
        hourly_count = await self.increment_counter(limiter, hourly_key, 3600)

        # Calculate remaining
        daily_remaining = max(0, limits['daily'] - daily_count)
        hourly_remaining = max(0, limits['hourly'] - hourly_count)

        # Determine if rate limited
        if daily_count > limits['daily'] or hourly_count > limits['hourly']:
            reset_time = self.get_reset_time(hourly_count > limits['hourly'])
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "tier": tier,
                    "reset_at": reset_time.isoformat(),
                    "upgrade_url": "/pricing"
                },
                headers={
                    "X-RateLimit-Limit": str(limits['hourly']),
                    "X-RateLimit-Remaining": str(min(daily_remaining, hourly_remaining)),
                    "X-RateLimit-Reset": str(int(reset_time.timestamp())),
                    "Retry-After": str(int((reset_time - datetime.now()).total_seconds()))
                }
            )

        return {
            "tier": tier,
            "daily_remaining": daily_remaining,
            "hourly_remaining": hourly_remaining,
            "daily_limit": limits['daily'],
            "hourly_limit": limits['hourly']
        }

    async def increment_counter(self, client, key: str, ttl: int) -> int:
        """Increment and return counter value"""
        if isinstance(client, aioredis.Redis):
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            results = await pipe.execute()
            return results[0]
        else:
            # Fallback to in-memory implementation
            return await client.increment(key, ttl)

    def get_reset_time(self, is_hourly: bool) -> datetime:
        """Calculate when rate limit resets"""
        now = datetime.now()
        if is_hourly:
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
```

### 3. In-Memory Fallback Limiter

```python
from collections import defaultdict
import time
import asyncio

class InMemoryRateLimiter:
    """Fallback rate limiter when Redis is unavailable"""

    def __init__(self):
        self.counters = defaultdict(lambda: {"count": 0, "expires": 0})
        self.lock = asyncio.Lock()

    async def increment(self, key: str, ttl: int) -> int:
        async with self.lock:
            now = time.time()

            # Clean expired entries
            if self.counters[key]["expires"] < now:
                self.counters[key] = {"count": 0, "expires": now + ttl}

            self.counters[key]["count"] += 1

            # Periodic cleanup of old entries
            if len(self.counters) > 10000:
                await self._cleanup_expired()

            return self.counters[key]["count"]

    async def _cleanup_expired(self):
        now = time.time()
        expired_keys = [k for k, v in self.counters.items() if v["expires"] < now]
        for key in expired_keys:
            del self.counters[key]
```

### 4. FastAPI Middleware Integration

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: TieredRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Skip for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        # Check rate limits
        try:
            rate_info = await self.rate_limiter.check_rate_limit(request)

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Tier"] = rate_info["tier"]
            response.headers["X-RateLimit-Remaining-Daily"] = str(rate_info["daily_remaining"])
            response.headers["X-RateLimit-Remaining-Hourly"] = str(rate_info["hourly_remaining"])

            return response

        except HTTPException as e:
            # Rate limit exceeded
            return Response(
                content=json.dumps(e.detail),
                status_code=e.status_code,
                headers=e.headers,
                media_type="application/json"
            )
```

### 5. Session Management for Better Tracking

```python
from fastapi import Cookie, Response
import uuid
from typing import Optional

class SessionManager:
    def get_or_create_session(
        self,
        response: Response,
        session_id: Optional[str] = Cookie(None)
    ) -> str:
        """Get existing session or create new one"""
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(
                key="session_id",
                value=session_id,
                max_age=86400 * 30,  # 30 days
                httponly=True,
                secure=True,  # HTTPS only
                samesite="strict"
            )
        return session_id
```

### 6. Client-Side Usage Tracking

```typescript
// Frontend component to display rate limits
interface RateLimitInfo {
  tier: string;
  dailyRemaining: number;
  hourlyRemaining: number;
  dailyLimit: number;
  hourlyLimit: number;
}

export function RateLimitDisplay({ info }: { info: RateLimitInfo }) {
  const dailyPercentage = (info.dailyRemaining / info.dailyLimit) * 100;
  const hourlyPercentage = (info.hourlyRemaining / info.hourlyLimit) * 100;

  return (
    <div className="rate-limit-info">
      <h3>Usage Limits ({info.tier} tier)</h3>
      <div className="limit-bar">
        <label>Daily: {info.dailyRemaining}/{info.dailyLimit}</label>
        <progress value={dailyPercentage} max="100" />
      </div>
      <div className="limit-bar">
        <label>Hourly: {info.hourlyRemaining}/{info.hourlyLimit}</label>
        <progress value={hourlyPercentage} max="100" />
      </div>
      {info.dailyRemaining < 5 && (
        <p className="warning">
          Running low on analyses.
          <a href="/pricing">Upgrade for more</a>
        </p>
      )}
    </div>
  );
}
```

## Implementation Steps

1. Set up Azure Cache for Redis instance
2. Create Redis connection manager with SSL
3. Implement TieredRateLimiter class
4. Create in-memory fallback limiter
5. Add FastAPI middleware for rate limiting
6. Implement session management
7. Create rate limit status endpoint
8. Add frontend components for usage display
9. Write comprehensive tests
10. Document rate limit behavior

## Testing Requirements

### Unit Tests
- Test rate limit calculation logic
- Test client ID generation
- Test Redis failure fallback
- Test header generation
- Test tier-based limits

### Integration Tests
- Test with real Redis instance
- Test concurrent requests
- Test session persistence
- Test rate limit reset timing
- Test middleware integration

### Load Tests
- Verify sub-second response times
- Test with 1000+ concurrent clients
- Verify Redis connection pooling
- Test memory usage of fallback limiter

## Acceptance Criteria

- [ ] Rate limits enforced per tier (20/100/1000 daily)
- [ ] Proper HTTP 429 responses with headers
- [ ] Redis integration with Azure Cache
- [ ] Fallback to in-memory when Redis unavailable
- [ ] Session-based tracking implemented
- [ ] Rate limit status visible in UI
- [ ] Reset times calculated correctly
- [ ] 95% test coverage
- [ ] Performance under 50ms per check

## Configuration

```yaml
# Environment variables
AZURE_REDIS_CONNECTION_STRING: "rediss://..."
RATE_LIMIT_ENABLED: "true"
RATE_LIMIT_FALLBACK_ENABLED: "true"
DEFAULT_TIER: "anonymous"
```

## Error Handling

1. **Redis Connection Failure**: Automatic fallback to in-memory
2. **Invalid Client ID**: Default to IP-based limiting
3. **Missing Headers**: Use reasonable defaults
4. **Clock Drift**: Use server time only

## Notes

- Redis keys expire automatically to prevent memory bloat
- In-memory fallback limited to 10,000 entries
- Session cookies enhance tracking but aren't required
- Consider implementing distributed rate limiting for multi-instance deployment
- Future enhancement: Add per-endpoint rate limits
- Monitor Redis memory usage and adjust TTLs if needed