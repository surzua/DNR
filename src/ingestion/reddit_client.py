"""Cliente de Reddit para monitoreo de debates ciudadanos en subreddits chilenos.

Implementa estrategia dual (JSON / RSS fallback), filtrado por engagement y degradación suave.
"""

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
import feedparser
import requests
import yaml

from src.ingestion.http_client import DEFAULT_HEADERS
from src.ingestion.models import NewsArticle

logger = logging.getLogger("dnr.reddit_client")

SUBREDDIT_REGEX = re.compile(r"^[a-zA-Z0-9_]{1,50}$")


def parse_reddit_json_post(
    post_data: Dict[str, Any],
    subreddit: str,
    cutoff_time: Optional[datetime] = None,
    min_score: int = 50,
    min_comments: int = 30,
) -> Optional[NewsArticle]:
    """Parsea un post individual obtenido via API JSON de Reddit."""
    title = post_data.get("title", "").strip()
    permalink = post_data.get("permalink", "").strip()
    if not title or not permalink:
        return None

    score = post_data.get("score", 0)
    num_comments = post_data.get("num_comments", 0)

    # Filtrar por umbral de viralidad/engagement
    if score < min_score and num_comments < min_comments:
        return None

    # Filtrar por fecha
    created_utc = post_data.get("created_utc")
    if created_utc:
        pub_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    else:
        pub_dt = datetime.now(timezone.utc)

    if cutoff_time and pub_dt < cutoff_time:
        return None

    full_link = f"https://www.reddit.com{permalink}"
    selftext = post_data.get("selftext", "")[:500]
    summary = selftext if selftext else f"[Score: {score} | Comentarios: {num_comments}]"

    return NewsArticle(
        title=title,
        link=full_link,
        summary=summary,
        published_at=pub_dt,
        source=f"Reddit (r/{subreddit})",
        category="Debate & Comunidad",
        score=score,
        comments_count=num_comments,
    )


def parse_reddit_rss_entry(
    entry: Any,
    subreddit: str,
    cutoff_time: Optional[datetime] = None,
) -> Optional[NewsArticle]:
    """Parsea una entrada de feed RSS de Reddit (.rss)."""
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    if not title or not link:
        return None

    pub_dt: Optional[datetime] = None
    upd_parsed = entry.get("updated_parsed")
    pub_parsed = entry.get("published_parsed")
    if upd_parsed:
        try:
            pub_dt = datetime(*upd_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pub_dt = None
    elif pub_parsed:
        try:
            pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pub_dt = None

    if pub_dt is None:
        pub_dt = datetime.now(timezone.utc)

    if cutoff_time and pub_dt < cutoff_time:
        return None

    content_list = entry.get("content", [])
    raw_content = content_list[0].get("value", "") if content_list else entry.get("summary", "")

    return NewsArticle(
        title=title,
        link=link,
        summary=raw_content[:500],
        published_at=pub_dt,
        source=f"Reddit (r/{subreddit})",
        category="Debate & Comunidad",
    )


def fetch_subreddit_posts(
    subreddit: str,
    min_score: int = 50,
    min_comments: int = 30,
    limit: int = 50,
    cutoff_time: Optional[datetime] = None,
    timeout: int = 10,
) -> List[NewsArticle]:
    """Obtiene publicaciones de un subreddit usando estrategia dual (JSON con fallback a RSS)."""
    headers = {
        **DEFAULT_HEADERS,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    articles: List[NewsArticle] = []
    if not subreddit or not SUBREDDIT_REGEX.match(subreddit.strip()):
        logger.warning("Nombre de subreddit inválido o con caracteres no permitidos: %r", subreddit)
        return []

    # Intento 1: API JSON
    clean_sub = subreddit.strip()
    json_url = f"https://www.reddit.com/r/{clean_sub}/hot.json?limit={limit}"
    logger.info("Consultando Reddit JSON: r/%s", clean_sub)
    try:
        response = requests.get(json_url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            children = list(data.get("data", {}).get("children", []))

            # Si la ventana temporal es mayor a 24 horas (ej. 3 o 7 días), consultar también top semanal
            now = datetime.now(timezone.utc)
            if cutoff_time and (now - cutoff_time).total_seconds() > 90000:
                top_url = f"https://www.reddit.com/r/{clean_sub}/top.json?t=week&limit={limit}"
                try:
                    time.sleep(1)
                    top_resp = requests.get(top_url, headers=headers, timeout=timeout)
                    if top_resp.status_code == 200:
                        top_children = top_resp.json().get("data", {}).get("children", [])
                        seen_permalinks = {
                            c.get("data", {}).get("permalink")
                            for c in children
                            if c.get("data", {}).get("permalink")
                        }
                        for tc in top_children:
                            plink = tc.get("data", {}).get("permalink")
                            if plink and plink not in seen_permalinks:
                                children.append(tc)
                                seen_permalinks.add(plink)
                except Exception as top_exc:
                    logger.warning("No se pudo obtener Reddit top semanal para r/%s: %s", clean_sub, top_exc)

            for child in children:
                post_data = child.get("data", {})
                art = parse_reddit_json_post(
                    post_data=post_data,
                    subreddit=subreddit,
                    cutoff_time=cutoff_time,
                    min_score=min_score,
                    min_comments=min_comments,
                )
                if art:
                    articles.append(art)
            logger.info("Reddit JSON r/%s: %d hilos filtrados con éxito", subreddit, len(articles))
            return articles
        else:
            logger.warning(
                "Reddit JSON r/%s retornó HTTP %d. Intentando fallback a RSS...",
                subreddit,
                response.status_code,
            )
    except Exception as exc:
        logger.warning("Fallo al conectar con Reddit JSON r/%s: %s. Probando fallback RSS...", subreddit, exc)

    # Intento 2: Fallback a RSS
    rss_url = f"https://www.reddit.com/r/{clean_sub}/.rss"
    try:
        response = requests.get(rss_url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                art = parse_reddit_rss_entry(
                    entry=entry,
                    subreddit=subreddit,
                    cutoff_time=cutoff_time,
                )
                if art:
                    articles.append(art)
            logger.info("Reddit RSS fallback r/%s: %d hilos recuperados", subreddit, len(articles))
        else:
            logger.warning(
                "Reddit RSS r/%s retornó HTTP %d (posible rate limit temporal). Omitiendo subreddit.",
                subreddit,
                response.status_code,
            )
    except Exception as exc:
        logger.warning("Fallo en fallback RSS de Reddit r/%s: %s", subreddit, exc)

    return articles


def fetch_reddit_threads(
    config_path: str = "config/sources.yaml",
    lookback_hours: Optional[int] = None,
) -> List[NewsArticle]:
    """Obtiene hilos destacados de todos los subreddits configurados.

    Garantiza tolerancia a fallos: nunca bloquea la ejecución del pipeline ante caídas o rate limits.
    """
    path = Path(config_path)
    if not path.exists():
        logger.error("Archivo de configuración %s no encontrado", config_path)
        return []

    with open(path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f) or {}

    reddit_cfg = config.get("reddit", {})
    subreddits = reddit_cfg.get("subreddits", [])
    if not subreddits:
        logger.info("No hay subreddits configurados en %s", config_path)
        return []

    filters = reddit_cfg.get("filters", {})
    min_score = filters.get("min_score", 50)
    min_comments = filters.get("min_comments", 30)
    limit = filters.get("limit", 50)

    pipeline_cfg = config.get("pipeline", {})
    hours = lookback_hours if lookback_hours is not None else pipeline_cfg.get("max_hours_lookback", 24)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    all_articles: List[NewsArticle] = []

    for idx, sub in enumerate(subreddits):
        if idx > 0:
            # Pausa para mitigar rate limiting entre consultas secuenciales a Reddit
            time.sleep(2)

        sub_articles = fetch_subreddit_posts(
            subreddit=sub,
            min_score=min_score,
            min_comments=min_comments,
            limit=limit,
            cutoff_time=cutoff_time,
        )
        all_articles.extend(sub_articles)

    logger.info("Ingesta Reddit completada: %d hilos totales recopilados", len(all_articles))
    return all_articles
