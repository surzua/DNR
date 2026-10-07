"""Unit tests for http_client security features and resilience."""

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.ingestion.http_client import fetch_url_content


def test_fetch_url_content_rejects_unsafe_schemes():
    assert fetch_url_content("ftp://servidor.com/feed.xml") is None
    assert fetch_url_content("file:///etc/passwd") is None
    assert fetch_url_content("javascript:alert(1)") is None
    assert fetch_url_content("http://") is None
    assert fetch_url_content("") is None


@patch("src.ingestion.http_client.requests.get")
def test_fetch_url_content_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.encoding = "utf-8"
    mock_resp.iter_content.return_value = [b"line1\n", b"line2\n"]
    mock_get.return_value = mock_resp

    text = fetch_url_content("https://noticias.cl/rss")
    assert text == "line1\nline2\n"
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["stream"] is True


@patch("src.ingestion.http_client.requests.get")
def test_fetch_url_content_enforces_max_bytes(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.encoding = "utf-8"
    # Chunk de 100 bytes en stream
    mock_resp.iter_content.return_value = [b"A" * 50, b"B" * 50, b"C" * 50]
    mock_get.return_value = mock_resp

    # Limitar a 60 bytes
    text = fetch_url_content("https://noticias.cl/huge.xml", max_bytes=60)
    assert len(text) == 60
    assert text.startswith("A" * 50)
    assert text.endswith("B" * 10)


@patch("src.ingestion.http_client.requests.get")
def test_fetch_url_content_handles_network_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("DNS failure")
    assert fetch_url_content("https://inaccesible.cl/rss") is None
