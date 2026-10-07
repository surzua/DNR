"""Unit tests for the Reddit ingestion module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest

from src.ingestion.reddit_client import (
    fetch_reddit_threads,
    fetch_subreddit_posts,
    parse_reddit_json_post,
    parse_reddit_rss_entry,
)


def test_parse_reddit_json_post():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # Post con alto score (cumple umbral)
    valid_data = {
        "title": "Debate sobre tarifas de transporte en Santiago",
        "permalink": "/r/chile/comments/abc123/debate/",
        "selftext": "Opiniones sobre la nueva alza...",
        "score": 120,
        "num_comments": 45,
        "created_utc": (now - timedelta(hours=3)).timestamp(),
    }
    article = parse_reddit_json_post(
        post_data=valid_data,
        subreddit="chile",
        cutoff_time=cutoff,
        min_score=50,
        min_comments=30,
    )
    assert article is not None
    assert article.title == "Debate sobre tarifas de transporte en Santiago"
    assert article.link == "https://www.reddit.com/r/chile/comments/abc123/debate/"
    assert article.score == 120
    assert article.comments_count == 45
    assert article.source == "Reddit (r/chile)"

    # Post con bajo engagement (rechazado)
    low_engagement = {
        "title": "Foto de mi gato",
        "permalink": "/r/chile/comments/cat/",
        "score": 10,
        "num_comments": 5,
        "created_utc": (now - timedelta(hours=1)).timestamp(),
    }
    assert parse_reddit_json_post(low_engagement, subreddit="chile", min_score=50, min_comments=30) is None

    # Post fuera de la ventana de 24h (rechazado)
    old_post = {
        "title": "Noticia de la semana pasada",
        "permalink": "/r/chile/comments/old/",
        "score": 300,
        "num_comments": 100,
        "created_utc": (now - timedelta(hours=48)).timestamp(),
    }
    assert parse_reddit_json_post(old_post, subreddit="chile", cutoff_time=cutoff) is None


def test_parse_reddit_rss_entry():
    now = datetime.now(timezone.utc)
    entry = {
        "title": "Hilo de discusión en Reddit",
        "link": "https://www.reddit.com/r/chile/comments/xyz/",
        "updated_parsed": (now - timedelta(hours=1)).timetuple(),
        "content": [{"value": "<p>Contenido del post</p>"}],
    }
    article = parse_reddit_rss_entry(entry, subreddit="chile")
    assert article is not None
    assert article.title == "Hilo de discusión en Reddit"
    assert article.source == "Reddit (r/chile)"
    assert article.summary == "Contenido del post"


@patch("src.ingestion.reddit_client.requests.get")
def test_fetch_subreddit_posts_json_success(mock_get):
    now = datetime.now(timezone.utc)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Post viral",
                        "permalink": "/r/chile/comments/viral/",
                        "score": 150,
                        "num_comments": 80,
                        "created_utc": (now - timedelta(hours=2)).timestamp(),
                    }
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    articles = fetch_subreddit_posts(subreddit="chile", min_score=50, min_comments=30)
    assert len(articles) == 1
    assert articles[0].title == "Post viral"


@patch("src.ingestion.reddit_client.feedparser.parse")
@patch("src.ingestion.reddit_client.requests.get")
def test_fetch_subreddit_posts_fallback_to_rss(mock_get, mock_feedparser):
    # Simula JSON retornando 403 y luego RSS retornando 200
    json_resp = MagicMock()
    json_resp.status_code = 403

    rss_resp = MagicMock()
    rss_resp.status_code = 200
    rss_resp.text = "<rss></rss>"

    mock_get.side_effect = [json_resp, rss_resp]

    mock_feed = MagicMock()
    mock_feed.entries = [
        {
            "title": "Noticia recuperada via RSS",
            "link": "https://www.reddit.com/r/chile/comments/rss/",
        }
    ]
    mock_feedparser.return_value = mock_feed

    articles = fetch_subreddit_posts(subreddit="chile")
    assert len(articles) == 1
    assert articles[0].title == "Noticia recuperada via RSS"


@patch("src.ingestion.reddit_client.requests.get")
def test_fetch_subreddit_posts_both_fail_gracefully(mock_get):
    # Ambos intentos fallan (error de red)
    mock_get.side_effect = Exception("Network down")

    articles = fetch_subreddit_posts(subreddit="chile")
    assert articles == []
