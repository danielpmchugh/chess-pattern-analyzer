# Task: API-001 - Chess.com API Integration Module

**Status**: `todo`
**Priority**: Critical
**Assigned Agent**: backend-developer (to be created)
**Estimated Effort**: 1-2 days
**Dependencies**: None

## Objective

Create a robust service module for fetching public game data from the Chess.com Published-Data API (PubAPI) without requiring authentication, including proper error handling, rate limiting, and data parsing.

## Success Criteria

1. Successfully fetch game history for any valid Chess.com username
2. Parse PGN data from API responses
3. Handle API errors gracefully (404 for invalid users, 429 for rate limits)
4. Implement exponential backoff for retries
5. Support fetching games by date range
6. Process 100 games in under 30 seconds

## Technical Approach

### 1. API Client Structure

```python
class ChessComAPIClient:
    BASE_URL = "https://api.chess.com/pub"

    def __init__(self, rate_limiter=None):
        self.session = requests.Session()
        self.rate_limiter = rate_limiter

    async def get_player_games(self, username: str, year: int, month: int) -> List[Game]:
        """Fetch games for a specific month"""
        pass

    async def get_player_profile(self, username: str) -> PlayerProfile:
        """Validate username and get profile"""
        pass

    async def fetch_game_range(self, username: str, start_date: date, end_date: date) -> List[Game]:
        """Fetch all games in date range"""
        pass
```

### 2. Key Endpoints to Implement

- `GET /player/{username}` - Validate username exists
- `GET /player/{username}/games/{YYYY}/{MM}` - Fetch monthly games
- `GET /player/{username}/stats` - Get player statistics (optional)

### 3. Response Handling

```python
def parse_game_response(self, response: dict) -> List[Game]:
    """Parse API response into Game objects"""
    games = []
    for game_data in response.get('games', []):
        game = Game(
            url=game_data['url'],
            pgn=game_data.get('pgn'),
            time_control=game_data['time_control'],
            end_time=game_data['end_time'],
            rated=game_data['rated'],
            white_username=game_data['white']['username'],
            white_rating=game_data['white']['rating'],
            black_username=game_data['black']['username'],
            black_rating=game_data['black']['rating'],
            result=self.parse_result(game_data)
        )
        games.append(game)
    return games
```

### 4. Error Handling Strategy

```python
class ChessComAPIError(Exception):
    pass

class UserNotFoundException(ChessComAPIError):
    pass

class RateLimitException(ChessComAPIError):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after

async def handle_response(self, response):
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        raise UserNotFoundException(f"User not found")
    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After', 60)
        raise RateLimitException(retry_after)
    else:
        raise ChessComAPIError(f"API error: {response.status_code}")
```

### 5. Rate Limiting Implementation

```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.last_request = 0
        self.min_interval = 0.5  # Start with 500ms between requests

    async def wait_if_needed(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = time.time()

    def adjust_rate(self, got_429: bool):
        if got_429:
            self.min_interval = min(self.min_interval * 2, 10)  # Max 10s
        else:
            self.min_interval = max(self.min_interval * 0.95, 0.1)  # Min 100ms
```

### 6. Caching Strategy

```python
class GameCache:
    def __init__(self, ttl=43200):  # 12 hours default
        self.cache = {}
        self.ttl = ttl

    def cache_key(self, username: str, year: int, month: int) -> str:
        return f"{username}:{year}:{month}"

    def get(self, username: str, year: int, month: int) -> Optional[List[Game]]:
        key = self.cache_key(username, year, month)
        if key in self.cache:
            games, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return games
        return None

    def set(self, username: str, year: int, month: int, games: List[Game]):
        key = self.cache_key(username, year, month)
        self.cache[key] = (games, time.time())
```

## Implementation Steps

1. Create base API client class with session management
2. Implement individual endpoint methods
3. Add PGN parsing using python-chess library
4. Implement retry logic with exponential backoff
5. Add caching layer for 12-hour data freshness
6. Create comprehensive error handling
7. Write unit tests for all methods
8. Add integration tests with mock server
9. Document usage examples

## Testing Requirements

### Unit Tests
- Test PGN parsing with various game formats
- Test error handling for all HTTP status codes
- Test rate limiter behavior
- Test cache hit/miss scenarios

### Integration Tests
- Test with real Chess.com API (limited)
- Test with invalid usernames
- Test date range fetching
- Test retry behavior on 429 responses

## Acceptance Criteria

- [ ] Can fetch games for valid Chess.com username
- [ ] Returns appropriate error for invalid username
- [ ] Handles rate limiting without crashing
- [ ] Parses PGN data correctly
- [ ] Implements caching with 12-hour TTL
- [ ] Includes comprehensive error handling
- [ ] Has 90%+ test coverage
- [ ] Documentation includes usage examples

## Example Usage

```python
# Initialize client
client = ChessComAPIClient()

# Validate username
try:
    profile = await client.get_player_profile("magnus")
except UserNotFoundException:
    return {"error": "Username not found"}

# Fetch last 3 months of games
end_date = datetime.now()
start_date = end_date - timedelta(days=90)
games = await client.fetch_game_range("magnus", start_date, end_date)

# Games are now ready for analysis
print(f"Fetched {len(games)} games for analysis")
```

## Notes

- No authentication required for public data
- Chess.com data refreshes at most every 12 hours
- Serial requests are unlimited, parallel requests may hit rate limits
- Consider implementing progress callback for large date ranges
- PGN parsing should handle various time controls and variants