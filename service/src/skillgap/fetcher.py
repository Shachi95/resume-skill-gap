"""HTTP fetcher with robots.txt checking and rate limiting."""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

_USER_AGENT = "skillgap-fetcher/0.1"


class RobotsDisallowedError(Exception):
    """Raised when robots.txt disallows fetching the URL."""


def _check_robots(url: str, *, client: httpx.Client) -> None:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    try:
        resp = client.get(robots_url)
        resp.raise_for_status()
        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())
    except httpx.HTTPStatusError:
        return
    if not rp.can_fetch(_USER_AGENT, url):
        raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")


_last_request_time: float = 0.0


def fetch(url: str, *, rate_limit: float = 1.0, timeout: float = 30.0) -> str:
    """Fetch raw HTML from a URL.

    Args:
        url: The URL to fetch.
        rate_limit: Maximum requests per second.
        timeout: HTTP timeout in seconds.

    Returns:
        Raw HTML as a string.

    Raises:
        RobotsDisallowedError: If robots.txt disallows the URL.
        httpx.HTTPStatusError: On 4xx/5xx responses.
    """
    global _last_request_time

    if rate_limit > 0:
        interval = 1.0 / rate_limit
        elapsed = time.monotonic() - _last_request_time
        if elapsed < interval:
            time.sleep(interval - elapsed)

    with httpx.Client(
        headers={"User-Agent": _USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        _check_robots(url, client=client)
        response = client.get(url)
        response.raise_for_status()
        _last_request_time = time.monotonic()
        return response.text
