#!/usr/bin/env python3
"""
Scrapes https://protraining.opentrader.com/coaching/ for links whose anchor
text begins with "Coaching/Q" and prints vimeo_download.py invocation lines.
"""

import argparse
import http.cookiejar
import re
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://protraining.opentrader.com/coaching/"

# Month name -> number mapping for parsing dates like "March 11th, 2026"
MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

DATE_PATTERN = re.compile(
    r"(\w+)\s+(\d+)(?:st|nd|rd|th)?,?\s+(\d{4})", re.IGNORECASE
)


def parse_date(text: str) -> str:
    """Extract and format date from anchor text as YYYYMMDD, or '' if not found."""
    m = DATE_PATTERN.search(text)
    if not m:
        return ""
    month_name, day, year = m.group(1), int(m.group(2)), int(m.group(3))
    month = MONTH_MAP.get(month_name.lower())
    if month is None:
        return ""
    return f"{year:04d}{month:02d}{day:02d}"


def scrape(session: requests.Session) -> None:
    response = session.get(URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found = 0

    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True)
        if not text.startswith("Coaching/Q"):
            continue

        href = tag["href"].strip()
        date_str = parse_date(text)

        print(
            f'python vimeo_download.py --keep-audio -m medium {href} '
            f'--output-dir "G:\\OpenTrader\\coaching-webinar\\{date_str}"'
        )
        found += 1

    if found == 0:
        print(
            "No 'Coaching/Q' links found. "
            "The page may require authentication — see README for details.",
            file=sys.stderr,
        )


def load_cookies_file(path: str) -> http.cookiejar.CookieJar:
    """Load a Netscape-format cookies.txt file (exported by browser extensions)."""
    jar = http.cookiejar.MozillaCookieJar(path)
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except http.cookiejar.LoadError as exc:
        print(f"Error loading cookies file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)
    return jar


def main() -> None:
    import os

    parser = argparse.ArgumentParser(
        description="Scrape Coaching/Q webinar links and print vimeo_download commands."
    )
    parser.add_argument(
        "--cookies",
        metavar="FILE",
        default=os.environ.get("OT_COOKIES"),
        help="Path to a Netscape cookies.txt file (or set OT_COOKIES env var).",
    )
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    if args.cookies:
        session.cookies = load_cookies_file(args.cookies)
    else:
        # Fall back to username/password login via environment variables.
        username = os.environ.get("OT_USERNAME")
        password = os.environ.get("OT_PASSWORD")

        if username and password:
            login_url = "https://protraining.opentrader.com/wp-login.php"
            payload = {
                "log": username,
                "pwd": password,
                "wp-submit": "Log In",
                "redirect_to": URL,
                "testcookie": "1",
            }
            session.get(login_url, timeout=30)  # grab initial cookies
            resp = session.post(login_url, data=payload, timeout=30)
            if "logout" not in resp.text.lower():
                print(
                    "Warning: login may have failed (no logout link detected).",
                    file=sys.stderr,
                )

    scrape(session)


if __name__ == "__main__":
    main()
