from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from html import escape

from config import load_settings
from models import FeedItem, HealthResponse
from services.collector import FeedCollector
from storage.repository import FeedRepository


settings = load_settings()
repository = FeedRepository(settings.app.database_path)
collector = FeedCollector(settings, repository)
scheduler = BackgroundScheduler(timezone="UTC")


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.app.admin_api_key:
        raise HTTPException(status_code=500, detail="admin_api_key_not_configured")

    if x_api_key != settings.app.admin_api_key:
        raise HTTPException(status_code=401, detail="invalid_api_key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository.initialize()
    collector.collect_once()

    scheduler.add_job(
        collector.collect_once,
        "interval",
        minutes=settings.app.poll_interval_minutes,
        id="collect-feeds",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Onboard Feeder",
    description="External feed ingestion microservice for Onboard Alert.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    items = repository.list_recent(limit=8)
    cards = "\n".join(
        f"""
        <article class="card">
          <div class="meta">
            <span>{escape(item.source_type.value)}</span>
            <span>{escape(item.source_name or "external source")}</span>
          </div>
          {f'<div class="location-pill">{escape(item.location_tag or item.location_city or "konum-var")}</div>' if item.has_location else '<div class="location-pill muted">konum-yok</div>'}
          <h2>{escape(item.title)}</h2>
          <p>{escape(item.description)}</p>
          <a href="{escape(str(item.source_url))}" target="_blank" rel="noopener noreferrer">
            Orijinal Kaynağı Aç ↗
          </a>
        </article>
        """
        for item in items
    )

    if not cards:
        cards = '<div class="empty">Henüz kayıt yok. /api/feeds/refresh endpointini çağır veya scheduler çalışsın.</div>'

    return f"""
    <!doctype html>
    <html lang="tr">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Onboard Feeder</title>
        <style>
          :root {{
            color-scheme: dark;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #020617;
            color: #e2e8f0;
          }}
          body {{
            margin: 0;
            min-height: 100vh;
            background:
              radial-gradient(circle at 20% 10%, rgba(34, 211, 238, 0.16), transparent 32rem),
              radial-gradient(circle at 90% 0%, rgba(16, 185, 129, 0.11), transparent 28rem),
              #020617;
          }}
          main {{
            max-width: 1120px;
            margin: 0 auto;
            padding: 40px 20px;
          }}
          .hero {{
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(15, 23, 42, 0.72);
            backdrop-filter: blur(16px);
            padding: 28px;
            box-shadow: 0 24px 70px rgba(0,0,0,0.35);
          }}
          .eyebrow {{
            margin: 0 0 10px;
            color: #67e8f9;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.22em;
            text-transform: uppercase;
          }}
          h1 {{
            margin: 0;
            font-size: clamp(32px, 5vw, 58px);
            line-height: 1;
            color: white;
          }}
          .sub {{
            max-width: 760px;
            color: #94a3b8;
            line-height: 1.7;
            margin: 18px 0 0;
          }}
          .stats {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 22px;
          }}
          .stat {{
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.045);
            padding: 14px;
          }}
          .stat strong {{
            display: block;
            color: white;
            font-size: 24px;
          }}
          .stat span {{
            color: #94a3b8;
            font-size: 12px;
            font-weight: 700;
          }}
          .actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 22px;
          }}
          .actions a {{
            border: 1px solid rgba(103,232,249,0.35);
            background: rgba(103,232,249,0.1);
            color: #cffafe;
            padding: 11px 14px;
            font-size: 14px;
            font-weight: 800;
            text-decoration: none;
          }}
          .section-title {{
            margin: 30px 0 14px;
            color: white;
            font-size: 18px;
          }}
          .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
          }}
          .card, .empty {{
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(15, 23, 42, 0.68);
            padding: 16px;
          }}
          .location-pill {{
            display: inline-flex;
            margin-top: 12px;
            border: 1px solid rgba(16,185,129,0.35);
            background: rgba(16,185,129,0.12);
            color: #a7f3d0;
            padding: 5px 8px;
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
          }}
          .location-pill.muted {{
            border-color: rgba(148,163,184,0.22);
            background: rgba(148,163,184,0.08);
            color: #94a3b8;
          }}
          .meta {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            color: #67e8f9;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
          }}
          .card h2 {{
            color: white;
            font-size: 17px;
            line-height: 1.35;
            margin: 12px 0 8px;
          }}
          .card p {{
            color: #cbd5e1;
            font-size: 14px;
            line-height: 1.65;
            margin: 0;
          }}
          .card a {{
            display: inline-flex;
            margin-top: 14px;
            color: #a7f3d0;
            font-size: 13px;
            font-weight: 800;
            text-decoration: none;
          }}
          @media (max-width: 720px) {{
            .stats {{ grid-template-columns: 1fr; }}
          }}
        </style>
      </head>
      <body>
        <main>
          <section class="hero">
            <p class="eyebrow">Onboard Feeder Microservice</p>
            <h1>External news feed collector is running.</h1>
            <p class="sub">
              Twitter/X hedefleri ve RSS haber kaynakları config dosyasından okunur,
              standart feed modeline dönüştürülür, SQLite içine kaydedilir ve REST API
              üzerinden onboard-alert projesine sunulur.
            </p>
            <div class="stats">
              <div class="stat"><strong>{repository.count()}</strong><span>Kayıt</span></div>
              <div class="stat"><strong>{repository.count_located()}</strong><span>Konumlu kayıt</span></div>
              <div class="stat"><strong>{len(settings.twitter.accounts) + len(settings.twitter.hashtags)}</strong><span>X hedefi</span></div>
              <div class="stat"><strong>{len(settings.rss_news.feeds)}</strong><span>RSS kaynağı</span></div>
            </div>
            <div class="actions">
              <a href="/api/health">Health JSON</a>
              <a href="/api/feeds?limit=20">Feeds JSON</a>
              <a href="/api/feeds?limit=20&location_only=true">Konumlu Feeds JSON</a>
              <a href="/docs">API Docs</a>
            </div>
          </section>

          <h2 class="section-title">Son Toplanan Kayıtlar</h2>
          <section class="grid">
            {cards}
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        service="onboard-feeder",
        stored_items=repository.count(),
        located_items=repository.count_located(),
    )


@app.get("/api/feeds", response_model=list[FeedItem])
def list_feeds(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    location_only: bool = Query(default=False),
) -> list[FeedItem]:
    return repository.list_recent(limit=limit, offset=offset, location_only=location_only)


@app.post("/api/feeds/refresh")
def refresh_feeds(_: None = Depends(require_admin_api_key)) -> dict[str, int]:
    return collector.collect_once()


@app.get("/api/sources/status")
def source_status() -> list[dict[str, object]]:
    return repository.list_source_status()
