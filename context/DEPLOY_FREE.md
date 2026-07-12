# DEPLOY\_FREE – FinAI on Free Tiers

This guide describes how to deploy **FinAI – Real-Time Financial Market Analytics** on **free tiers only**, with:

- **Frontend:** Vercel (Next.js)
- **Backend:** Render (FastAPI web service)
- **Database:** Postgres on Neon (recommended) or Supabase (alternative)

No paid services or credit cards are required beyond what these providers may need for account creation.

---

## 1. High-Level Deployment Topology

```text
                +-----------------------------+
                |  Vercel (Next.js frontend)  |
                |  apps/web                   |
                +---------------+-------------+
                                |
                                | HTTPS (REST JSON)
                                | WebSocket (ticks + alerts)
                                v
                +-----------------------------+
                |  Render (FastAPI backend)   |
                |  apps/api                   |
                +---------------+-------------+
                                |
                                | DATABASE_URL (managed)
                                v
                +-----------------------------+
                |  Neon or Supabase Postgres  |
                +-----------------------------+
```

---

## 2. Database (Free Postgres)

You need a **managed Postgres** instance reachable from Render.

### Option 1 (Recommended): Neon Free Tier

1. Create a Neon account and a new project.
2. In the Neon dashboard:
   - Create a **database** (e.g. `finai`).
   - Create a **user** (or use the default).
3. Find the **connection string** (often labeled “SQLAlchemy” or “psycopg2”).
   - It will look like:

     ```text
     postgresql://user:password@host.region.neon.tech:5432/dbname
     ```

4. For SQLAlchemy + psycopg2, prepend the driver:

   ```text
   postgresql+psycopg2://user:password@host.region.neon.tech:5432/dbname
   ```

5. You will use this as `DATABASE_URL` in Render (backend).

Notes:

- Neon free tier keeps storage persistent.
- Instances may **pause** when idle; first query wakes them up (slight latency).

---

### Option 2: Supabase Free Tier

1. Create a Supabase project.
2. In the project settings, locate the **connection string** for Postgres.
3. It will look like:

   ```text
   postgres://user:password@host.supabase.co:5432/postgres
   ```

4. For SQLAlchemy + psycopg2:

   ```text
   postgresql+psycopg2://user:password@host.supabase.co:5432/postgres
   ```

5. Use this as `DATABASE_URL` in Render.

Notes:

- Supabase free tier may **pause** after inactivity.
- Good enough for demos and low-traffic personal use.

---

### Applying Migrations on Managed DB

Once the Postgres database is available:

You must run **Alembic migrations** against it **once** (and whenever schema changes).

Inside a shell where `DATABASE_URL` points to the managed DB:

```bash
cd apps/api
alembic upgrade head
```

On Render, you can do this in one of two ways:

1. **One-off shell** (recommended for initial setup):

   - In the Render dashboard for the backend service, open a shell/SSH session.
   - Run:

     ```bash
     cd apps/api
     alembic upgrade head
     ```

2. **Build command hook** (optional):

   - Extend the Render **build command** (see Section 4) to include:

     ```bash
     cd apps/api && alembic upgrade head
     ```

   This keeps DB schema current on each deploy.

---

## 3. Frontend on Vercel (apps/web)

### 3.1 Import the GitHub Repo

1. Push your FinAI repo to GitHub.
2. In Vercel:
   - Click **“New Project”** → **“Import Git Repository”**.
   - Select your FinAI repo.

### 3.2 Configure Project Settings

- **Root Directory:** `apps/web`
- **Framework Preset:** Next.js (auto-detected)

Build settings:

- **Build Command:** `npm run build`
- **Install Command:** `npm install` (Vercel’s default is fine)
- **Output Directory:** (leave default – Next.js manages this)

### 3.3 Environment Variables (Vercel)

From `apps/web/.env.example`:

- `NEXT_PUBLIC_API_BASE_URL`
  - Example (Render backend):

    ```text
    https://your-api-service.onrender.com
    ```

- `NEXT_PUBLIC_WS_URL`
  - Example (Render backend with WebSocket):

    ```text
    wss://your-api-service.onrender.com/ws/stream
    ```

Set these in Vercel:

1. Go to **Settings → Environment Variables**.
2. Add for the appropriate environments (Preview / Production):

   - `NEXT_PUBLIC_API_BASE_URL = https://<your-render-backend>`
   - `NEXT_PUBLIC_WS_URL = wss://<your-render-backend>/ws/stream`

### 3.4 Redeploy

Any push to the tracked branch (e.g. `main`) will:

- Trigger `npm install`
- Run `npm run build`
- Deploy a new version of the frontend

---

## 4. Backend on Render (apps/api)

You will deploy FastAPI as a **Render Web Service** **without** any paid add-ons.

### 4.1 Create the Service

1. In Render, select **“New +” → “Web Service”**.
2. Choose **“Build and deploy from a Git repository”**.
3. Select your FinAI repo.

### 4.2 Configure Build & Runtime

Use the **Python environment** (no custom Docker required):

- **Root Directory:** `apps/api`
- **Environment:** Python 3.11
- **Build Command:**

  ```bash
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  ```

- **Start Command:**

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```

Render will expose an HTTPS endpoint, e.g.:

```text
https://your-api-service.onrender.com
```

WebSockets:

- Render free web services support WebSockets.
- Note: Free instances may **sleep** after inactivity:
  - Existing WebSocket connections will be closed.
  - The frontend `useRealtimePrices` hook handles reconnection and REST fallback.

### 4.3 Environment Variables (Render)

From `apps/api/.env.example`:

- **Core**

  - `ENV=production`
  - `DEBUG=false`
  - `LOG_LEVEL=INFO`

- **Database**

  - `DATABASE_URL` – your Neon or Supabase connection string in `postgresql+psycopg2://...` form.

- **Providers**

  - `TWELVE_DATA_API_KEY` – from Twelve Data dashboard (free tier).
  - `TWELVE_DATA_BASE_URL` (optional, default `https://api.twelvedata.com`).
  - `COINGECKO_BASE_URL` (default `https://api.coingecko.com/api/v3`).
  - `GDELT_BASE_URL` (default `https://api.gdeltproject.org/api/v2/doc/doc`).

- **AI research desk (optional)**

  - `ANTHROPIC_API_KEY` – from the [Anthropic Console](https://console.anthropic.com/). Leave unset to deploy without the `/research` feature; every other endpoint works fine without it.
  - `RESEARCH_MODEL` (default `claude-haiku-4-5`) – a full 3-agent research run costs roughly a cent on Haiku.
  - `RESEARCH_DAILY_LIMIT` (default `25`) – caps research runs per UTC day; important for a public demo since, unlike Twelve Data/CoinGecko/GDELT, Claude API usage is not free.

- **Caching / rate limiting** (optional to override; defaults are sensible):

  - `QUOTES_TTL_SECONDS` (e.g. `10`)
  - `HISTORY_TTL_SECONDS` (e.g. `600`)
  - `PROVIDER_RATE_LIMIT_CAPACITY` (e.g. `60`)
  - `PROVIDER_RATE_LIMIT_REFILL_PER_SECOND` (e.g. `1.0`)

- **Realtime / alerts** (optional overrides):

  - `WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS`
  - `WEBSOCKET_STREAM_INTERVAL_SECONDS`
  - `ALERTS_SCHEDULER_INTERVAL_SECONDS`
  - `ALERTS_MIN_EVENT_INTERVAL_SECONDS`
  - `ALERTS_RSI_PERIOD`
  - `ALERTS_MA_SHORT_WINDOW`
  - `ALERTS_MA_LONG_WINDOW`

- **CORS**

  - `BACKEND_CORS_ORIGINS`

    Example:

    ```text
    http://localhost:3000,https://your-frontend.vercel.app
    ```

    Include your Vercel domain (e.g. `https://finai-demo.vercel.app`).

Configure all of these via the Render dashboard under **Environment → Environment Variables**.  
**Do not commit secrets** like API keys or database passwords.

### 4.4 Health Check

Point Render’s health check (if configured) to:

```text
/health
```

You should see:

```json
{ "status": "ok", "message": "healthy", "timestamp": "..." }
```

---

## 5. Environment Variable Reference

### Backend (apps/api)

| Variable                               | Required? | Description                                                                                   |
| -------------------------------------- | --------- | --------------------------------------------------------------------------------------------- |
| `ENV`                                  | No        | Runtime environment (`local`, `test`, `staging`, `production`); use `production` on Render.  |
| `DEBUG`                                | No        | Enable debug features/logging (`true` / `false`).                                            |
| `LOG_LEVEL`                            | No        | Log level (`INFO`, `DEBUG`, etc.).                                                           |
| `DATABASE_URL`                         | **Yes**   | SQLAlchemy URL for Neon/Supabase Postgres (`postgresql+psycopg2://...`).                     |
| `TWELVE_DATA_API_KEY`                  | Yes\*     | Twelve Data API key (stocks); free key from Twelve Data dashboard.                           |
| `TWELVE_DATA_BASE_URL`                 | No        | Override for Twelve Data base URL (default `https://api.twelvedata.com`).                    |
| `COINGECKO_BASE_URL`                   | No        | CoinGecko base URL (default `https://api.coingecko.com/api/v3`).                             |
| `GDELT_BASE_URL`                       | No        | GDELT Doc 2.0 base URL (default `https://api.gdeltproject.org/api/v2/doc/doc`).              |
| `ANTHROPIC_API_KEY`                    | No        | Enables the AI research desk (`/api/v1/research`). Unset = feature disabled (503), rest of app unaffected. |
| `RESEARCH_MODEL`                       | No        | Claude model for research agents (default `claude-haiku-4-5`).                               |
| `RESEARCH_DAILY_LIMIT`                 | No        | Max research runs per UTC day (default `25`) — cost guard for public demos.                  |
| `NEWS_TTL_SECONDS`                     | No        | TTL for cached news responses per symbol (default `1800`).                                   |
| `QUOTES_TTL_SECONDS`                   | No        | TTL for quote cache entries in seconds (default `10`).                                       |
| `HISTORY_TTL_SECONDS`                  | No        | TTL for history cache entries in seconds (default `600`).                                    |
| `PROVIDER_RATE_LIMIT_CAPACITY`         | No        | Token bucket capacity per provider (default `60`).                                           |
| `PROVIDER_RATE_LIMIT_REFILL_PER_SECOND`| No        | Token refill rate per second (default `1.0`).                                                |
| `WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS` | No        | Interval between heartbeat messages to clients (default `25`).                               |
| `WEBSOCKET_STREAM_INTERVAL_SECONDS`    | No        | Polling interval for realtime streamer (default `5`).                                        |
| `ALERTS_SCHEDULER_INTERVAL_SECONDS`    | No        | Interval at which alerts are evaluated (default `60`).                                       |
| `ALERTS_MIN_EVENT_INTERVAL_SECONDS`    | No        | Cooldown per alert event (default `300`).                                                    |
| `ALERTS_RSI_PERIOD`                    | No        | RSI lookback window (default `14`).                                                          |
| `ALERTS_MA_SHORT_WINDOW`               | No        | Short MA window for MA cross alerts (default `10`).                                          |
| `ALERTS_MA_LONG_WINDOW`                | No        | Long MA window for MA cross alerts (default `30`).                                           |
| `BACKEND_CORS_ORIGINS`                 | Yes       | Comma-separated list of allowed origins (include Vercel + localhost).                        |

\* You can run without a Twelve Data key; stock endpoints will fail gracefully but crypto/news will still work.

### Frontend (apps/web)

| Variable                 | Required? | Description                                                                           |
| ------------------------ | --------- | ------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | **Yes**   | Base URL of the backend (`https://your-api-service.onrender.com`).                   |
| `NEXT_PUBLIC_WS_URL`      | **Yes**   | WebSocket URL for realtime ticks (`wss://your-api-service.onrender.com/ws/stream`). |

---

## 6. Free-Tier Behaviour & Tuning

To stay well within free-tier limits:

- **Batch symbol requests**:
  - The backend already batches watchlist symbols by type.
- **Use caching aggressively**:
  - Quotes and history are cached with TTL.
  - News responses are cached per symbol/asset type.
- **Handle provider failures gracefully**:
  - Twelve Data, CoinGecko, GDELT:
    - Use HTTP timeouts.
    - Use exponential backoff + retries for 429/5xx.
    - Fall back to stale cached data (marked `is_stale`) or empty lists where applicable.
- **Tune polling** (for production):

  In `apps/api` env (Render):

  ```env
  WEBSOCKET_STREAM_INTERVAL_SECONDS=10
  QUOTES_TTL_SECONDS=20
  ```

  This reduces external API pressure at the cost of slightly less “live” updates.

---

## 7. Post-Deploy Validation Checklist

After both backend and frontend are deployed:

### 7.1 Backend

1. Visit:

   ```text
   https://your-api-service.onrender.com/health
   ```

   Expected JSON:

   ```json
   { "status": "ok", "message": "healthy", "timestamp": "..." }
   ```

2. Test a sample endpoint:

   ```bash
   curl "https://your-api-service.onrender.com/api/v1/quotes?symbols=BTC&asset_type=crypto"
   ```

   You should receive a JSON response (fields may be empty if providers are unavailable).

3. Optional: confirm `/docs` (Swagger UI) is reachable.

### 7.2 Frontend

1. Navigate to the Vercel URL, e.g.:

   ```text
   https://your-frontend.vercel.app
   ```

2. On the **Home** page:
   - Confirm any “Server Status” indicator shows healthy.
3. On the **Watchlist** page:
   - Add a symbol (e.g. `AAPL`, `BTC`).
   - Confirm prices load and update over time.

### 7.3 WebSocket

1. From the frontend’s watchlist or symbol page:
   - Open developer tools → Network → WS.
   - Check there is a connection to `/ws/stream` on the Render backend.
2. Temporarily disconnect the backend:
   - You should see the frontend fall back to periodic REST polling.

### 7.4 News & Sentiment

1. Open a symbol detail page (e.g. `/symbol/AAPL`).
2. Confirm the **News & Sentiment** panel:
   - Shows recent headlines (if available from GDELT).
   - Displays sentiment labels (positive/neutral/negative) and explanations.
   - Falls back to a clear “no recent headlines” message if empty.

### 7.5 Portfolio / Analytics / Alerts

1. Use the UI to:
   - Create a **holding** and open the **Portfolio** page.
   - Create an **alert** on `/alerts`.
2. Visit the **Analytics** page:
   - Confirm risk metrics and charts render.
3. Trigger alerts (manually or by using `/alerts/{id}/test-evaluate` via the docs) and:
   - Check they appear in the **Notification Center**.
   - Confirm they are also visible under `/api/v1/alerts/events`.

---

## 8. Security & Operational Notes

- **Secrets**:
  - Never commit `.env` files or hard-code API keys / DB URLs.
  - Keep all secrets in Vercel / Render / Neon / Supabase env variable UIs.
- **Ingress**:
  - Only the backend HTTP/WS endpoints and frontend are publicly exposed.
  - The database is accessed only via the backend using `DATABASE_URL`.
- **Cold starts**:
  - Render free services and Neon/Supabase free instances may **sleep**.
  - Expect slightly higher latency for the first request after inactivity.
  - The frontend already implements reconnection and REST fallback for realtime features.

With these steps, you have a **fully free-tier** deployment path for FinAI:

- Vercel (Next.js)
- Render (FastAPI web service)
- Neon or Supabase (Postgres)

All while respecting provider rate limits and providing a robust, educational, and safe analytics experience.