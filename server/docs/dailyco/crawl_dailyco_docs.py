"""
Crawl Daily.co REST API documentation and save as AI-readable markdown.

This script dynamically fetches ALL Daily.co REST API documentation pages from their
sitemap and saves them as markdown files for easy AI consumption.

STANDALONE SCRIPT - Does not depend on project dependencies.

Requirements:
    pip install requests beautifulsoup4 html2text lxml

Usage:
    python docs/dailyco/crawl_dailyco_docs.py

The script will:
1. Fetch the complete sitemap from docs.daily.co
2. Extract all REST API reference URLs (120+ pages)
3. Crawl each page and strip navigation/headers
4. Save as clean markdown in docs/dailyco/rest-api/
"""

import time
from pathlib import Path
from urllib.parse import urlparse

import html2text
import requests
from bs4 import BeautifulSoup

SITEMAP_URL = "https://docs.daily.co/sitemap.xml"
REST_API_PATH_PREFIX = "/reference/rest-api/"


def fetch_rest_api_urls() -> list[str]:
    """Fetch all REST API documentation URLs from Daily.co sitemap."""
    print(f"Fetching sitemap from {SITEMAP_URL}...")

    try:
        response = requests.get(SITEMAP_URL, timeout=30)
        response.raise_for_status()

        # Parse sitemap XML
        soup = BeautifulSoup(response.text, "xml")

        # Extract all <loc> URLs that contain REST API paths
        urls = []
        for loc in soup.find_all("loc"):
            url = loc.get_text().strip()
            # Match both /reference/rest-api/ and /reference/rest-api (without trailing slash)
            if REST_API_PATH_PREFIX in url or url.endswith("/reference/rest-api"):
                urls.append(url)

        # Sort for consistent ordering
        urls.sort()

        print(f"Found {len(urls)} REST API documentation pages\n")
        return urls

    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        print("Falling back to empty list")
        return []


def url_to_filepath(url: str, base_dir: Path) -> Path:
    """Convert URL to local file path maintaining directory structure."""
    parsed = urlparse(url)
    path_parts = parsed.path.strip("/").split("/")

    # Remove 'reference' and 'rest-api' from path since base_dir is already rest-api/
    # URL: /reference/rest-api/rooms/create-room -> rooms/create-room
    if "reference" in path_parts:
        path_parts.remove("reference")
    if "rest-api" in path_parts:
        path_parts.remove("rest-api")

    # Handle root index case (when URL is exactly /reference/rest-api)
    if not path_parts:
        return base_dir / "index.md"

    # Create filename
    filename = f"{path_parts[-1]}.md"

    # Create directory path
    if len(path_parts) > 1:
        dir_path = base_dir / "/".join(path_parts[:-1])
    else:
        dir_path = base_dir

    return dir_path / filename


def crawl_page(url: str, output_path: Path) -> bool:
    """Crawl a single page and save as markdown."""
    try:
        print(f"Crawling: {url}")

        # Fetch HTML
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse HTML and remove navigation/header/footer elements
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove navigation, headers, footers, and other non-content elements
        for element in soup.find_all(["nav", "header", "footer", "aside"]):
            element.decompose()

        # Remove common class-based navigation elements
        for class_name in [
            "navigation",
            "nav",
            "sidebar",
            "menu",
            "header",
            "footer",
            "breadcrumb",
            "breadcrumbs",
        ]:
            for element in soup.find_all(
                class_=lambda x: x and class_name in x.lower()
            ):
                element.decompose()

        # Remove common ID-based navigation elements
        for id_name in [
            "nav",
            "navigation",
            "sidebar",
            "header",
            "footer",
            "breadcrumb",
        ]:
            for element in soup.find_all(id=lambda x: x and id_name in x.lower()):
                element.decompose()

        # Remove role-based navigation elements
        for element in soup.find_all(
            attrs={"role": ["navigation", "banner", "complementary"]}
        ):
            element.decompose()

        # Try to find main content area (common patterns in docs sites)
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(attrs={"role": "main"})
            or soup.find(class_=lambda x: x and "content" in x.lower())
        )

        if main_content:
            html_to_convert = str(main_content)
        else:
            # Fallback to body if we can't find main content
            body = soup.find("body")
            html_to_convert = str(body) if body else response.text

        # Convert to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap lines
        markdown = h.handle(html_to_convert)

        # Create directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add header with source URL
        content = f"# Source: {url}\n\n{markdown}"

        # Save markdown
        output_path.write_text(content, encoding="utf-8")
        print(f"  ✓ Saved to: {output_path}")
        return True

    except Exception as e:
        print(f"  ✗ Error crawling {url}: {e}")
        return False


def main():
    """Main crawling function."""
    # Determine output directory (we're in docs/dailyco/, output to docs/dailyco/rest-api/)
    script_dir = Path(__file__).parent
    docs_dir = script_dir / "rest-api"

    # Fetch all REST API URLs from sitemap
    urls = fetch_rest_api_urls()

    if not urls:
        print("No URLs found to crawl. Exiting.")
        return

    print(f"Output directory: {docs_dir}")
    print(f"Total pages to crawl: {len(urls)}\n")

    success_count = 0
    fail_count = 0

    for url in urls:
        output_path = url_to_filepath(url, docs_dir)
        success = crawl_page(url, output_path)

        if success:
            success_count += 1
        else:
            fail_count += 1

        # Small delay to be respectful
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Crawling complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed:  {fail_count}")
    print(f"  Output:  {docs_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
