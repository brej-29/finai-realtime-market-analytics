# Data Sources

This project uses **free-tier friendly** data providers for stocks and crypto. The design prioritizes:

- Staying within free-tier **rate limits**
- Avoiding any **paid APIs**
- Using **caching and aggregation** to minimize external calls

---

## 1. Stocks – Twelve Data

**Provider:** [Twelve Data](https://twelvedata.com)

**Usage (planned):**

- **Quotes:** latest price, change, percent change, etc.
- **Historical OHLC:** for candlestick charts and indicators

**Example endpoints:**

- `GET https://api.twelvedata.com/quote?symbol=AAPL,MSFT&apikey=...`
- `GET https://api.twelvedata.com/time_series?symbol=AAPL&interval=1h&outputsize=100&apikey=...`

**Rate-limit assumptions (free tier):**

- Exact limits may change; always check Twelve Data docs.
- We design assuming:
  - Per-minute and per-day request caps
  - Multi-symbol calls are **more efficient** than one-symbol-per-request
- Implementation uses:
  - **Token-bucket rate limiting** per provider instance
  - **In-memory cache** with TTL to avoid repeated calls

**Caching strategy:**

- Quotes:
  - Cache key: `(provider, asset_type, symbols)`
  - TTL: short (e.g., 5–15 seconds) – tunable via settings
- Historical data:
  - Cache key: `(provider, asset_type, symbol, interval, range)`
  - TTL: longer (e.g., 5–15 minutes) – tunable via settings

**Degradation behavior:**

- If rate limit is exceeded or the provider returns an error:
  - Prefer to return **stale cached data** with a flag indicating staleness
  - If no cache is available, return a well-structured provider error
- No secrets (like API keys) are ever logged.

---

## 2. Crypto – CoinGecko

**Provider:** [CoinGecko](https://www.coingecko.com/en/api/documentation)

**Usage (planned):**

- **Current prices** in a given currency (e.g., USD)
- **Market charts** (historical prices and volume) per crypto asset

**Example endpoints:**

- `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true`
- `GET https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=1`

**Rate-limit assumptions (free tier):**

- CoinGecko enforces reasonable rate limits for free usage.
- We design assuming:
  - Requests should be **batched** (multiple IDs per request where possible)
  - Polling intervals should avoid high-frequency streaming patterns
- Implementation uses:
  - Shared **RateLimitGuard** with configurable capacity and refill rate
  - **Caching** with TTL similar to Twelve Data

**Caching strategy:**

- Current prices:
  - Cache key: `(provider, asset_type, symbols)`
  - TTL: short (e.g., 5–15 seconds)
- Market charts:
  - TTL: medium (e.g., several minutes) to reduce repeated history fetches

**Degradation behavior:**

- On provider errors or rate-limit hits:
  - Return last cached quote/chart when available
  - Otherwise, respond with a structured error that the UI can handle gracefully

---

## 3. News and Sentiment – GDELT Doc 2.0

**Provider:** [GDELT](https://www.gdeltproject.org/) – Doc 2.0 API (no API key required)

**Usage:**

- Symbol-level news feed for stocks and crypto:
  - `GET /api/v1/news?symbol=AAPL&asset_type=stock`
- Under the hood:
  - Calls the Doc 2.0 API: `https://api.gdeltproject.org/api/v2/doc/doc`
  - Mode: `ArtList`, `format=json`, sorted by most recent
  - Time window: last few hours (configurable via code; currently 8h)
- Backend filters:
  - English-language articles only (to match VADER's lexicon)
  - Extracts title, URL, domain, language, and `seendate`

**Sentiment:**

- Implementation: `HeadlineSentimentAnalyzer` using **VADER** (`vaderSentiment` library)
- For each headline:
  - Computes compound sentiment score in `[-1, 1]`
  - Maps to label: `positive`, `neutral`, or `negative`
  - Extracts top positive/negative words from VADER's lexicon to build a short explanation
- Exposed via `NewsArticle.sentiment` payload in the API.

**Caching:**

- `GDELTClient` uses `InMemoryCache` under the key `("gdelt", symbol, asset_type)`.
- TTL configured via `NEWS_TTL_SECONDS` (default: 1800s / 30 minutes).
- This dramatically reduces repeated calls for the same symbol.

**Degradation behavior:**

- On HTTP errors / non-200 / JSON decode errors:
  - Log a warning and return an **empty list** of articles.
  - The UI falls back to a “No recent headlines” message.
- No retries are implemented by default to avoid hammering free-tier resources.

---

## 4. Caching & Rate Limiting Design

### In-Memory Cache (per API instance)

Implementation: `InMemoryCache` in `app/services/market_data/cache.py`

- Simple dict-like store:
  - Key: typically a tuple `(provider, asset_type, symbol or symbols, params...)`
  - Value: `{ "value": <payload>, "expires_at": datetime }`
- Thread-safe enough for typical FastAPI usage (single-process, async workers); if multi-process scaling is introduced, cache is per-process.
- TTL values configurable via environment variables.

**Future extension:** Replace or augment with Redis for:

- Multi-instance cache sharing
- Better observability on cache hit/miss patterns

### Rate Limit Guard

Implementation: `RateLimitGuard` in `app/services/market_data/rate_limiter.py`

- Simple **token bucket** model:
  - Capacity: max tokens
  - Refill rate: tokens per second
  - Each request consumes one token
- On empty bucket:
  - Provider call is rejected with a rate-limit exception
  - Callers can either:
    - Fallback to cached data
    - Delay / backoff before retrying

### Backoff & Retries

- Provider calls wrap HTTP requests with:
  - Small, bounded retry count (e.g., 2–3 attempts)
  - Exponential backoff with jitter
- All retries are still subject to rate limiting.

---

## 5. Database (Postgres)

The database is used for **user-level state** and **app configuration**, not raw tick data:

- `watchlists` and `watchlist_items`
- `holdings`
- `alerts` (conditions only, not schedules yet)

**Connection:**

- `DATABASE_URL` environment variable (Postgres URI)
- Local testing can use SQLite if configured in settings, but production is assumed to be Postgres.

**Migrations:**

- Managed via **Alembic**.
- Migrations are additive and reflect changes in ORM models.
- Strategy:
  - Create an initial baseline migration
  - Every schema change in future PRs must:
    - Update models
    - Add Alembic migration
    - Update `context/CHANGELOG.md` and `DECISIONS.md` if appropriate

---

## 6. Free-Tier Considerations

- **Avoid high-frequency polling:**
  - Background streaming intervals is set conservatively (e.g., several seconds) and configurable.
- **Batch requests:**
  - For Twelve Data and CoinGecko, use **multi-symbol endpoints** where possible.
- **Use cache aggressively:**
  - UI should not assume microsecond accuracy; minor staleness is acceptable.
- **Graceful degradation:**
  - When providers are unavailable, the app should:
    - Continue displaying stale prices with a warning
    - Clearly signal in the UI that data is delayed or partial

Whenever data-source usage changes (new endpoints, new providers, revised rate limits), this document should be updated to reflect:

- New endpoints and capabilities
- Any new constraints or quotas
- Changes to caching and rate limiting behavior