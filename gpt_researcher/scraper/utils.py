"""Utility functions for web scraping.

This module provides helper functions for extracting content, images,
and processing HTML from web pages.
"""

import hashlib
import logging
import re
from urllib.parse import parse_qs, urljoin, urlparse

import bs4
from bs4 import BeautifulSoup

# requests often defaults text/* without charset to ISO-8859-1, mangling UTF-8 Chinese.
_UNRELIABLE_ENCODINGS = frozenset(
    {
        "iso-8859-1",
        "latin-1",
        "latin1",
        "ascii",
        "us-ascii",
        "windows-1252",
        "cp1252",
    }
)
_META_CHARSET_RE = re.compile(
    br"""charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""",
    re.IGNORECASE,
)
_CONTENT_TYPE_CHARSET_RE = re.compile(
    r"charset\s*=\s*['\"]?\s*([^\s;'\"]+)",
    re.IGNORECASE,
)


def decode_html_bytes(
    content: bytes,
    declared_encoding: str | None = None,
    content_type: str | None = None,
) -> str:
    """Decode HTML bytes without expensive charset detection (no chardet).

    Order: Content-Type charset → meta charset (first 2KB) → trusted declared
    encoding → utf-8 → gb18030 → utf-8 with replacement.
    """
    if not content:
        return ""

    candidates: list[str] = []

    if content_type:
        match = _CONTENT_TYPE_CHARSET_RE.search(content_type)
        if match:
            candidates.append(match.group(1).strip())

    meta_match = _META_CHARSET_RE.search(content[:2048])
    if meta_match:
        candidates.append(meta_match.group(1).decode("ascii", errors="ignore"))

    if declared_encoding:
        normalized = declared_encoding.strip().lower().replace("_", "-")
        if normalized not in _UNRELIABLE_ENCODINGS:
            candidates.append(declared_encoding.strip())

    candidates.extend(("utf-8", "gb18030"))

    seen: set[str] = set()
    for encoding in candidates:
        key = encoding.lower().replace("_", "-")
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            return content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue

    return content.decode("utf-8", errors="replace")


def soup_from_http_response(response, parser: str = "lxml") -> BeautifulSoup:
    """Build BeautifulSoup from a requests-like response with correct encoding."""
    html = decode_html_bytes(
        response.content,
        declared_encoding=getattr(response, "encoding", None),
        content_type=(getattr(response, "headers", None) or {}).get("content-type"),
    )
    return BeautifulSoup(html, parser)


def get_relevant_images(soup: BeautifulSoup, url: str) -> list:
    """Extract relevant images from the page"""
    image_urls = []
    
    try:
        # Find all img tags with src attribute
        all_images = soup.find_all('img', src=True)
        
        for img in all_images:
            img_src = urljoin(url, img['src'])
            if img_src.startswith(('http://', 'https://')):
                score = 0
                # Check for relevant classes
                if any(cls in img.get('class', []) for cls in ['header', 'featured', 'hero', 'thumbnail', 'main', 'content']):
                    score = 4  # Higher score
                # Check for size attributes
                elif img.get('width') and img.get('height'):
                    width = parse_dimension(img['width'])
                    height = parse_dimension(img['height'])
                    if width and height:
                        if width >= 2000 and height >= 1000:
                            score = 3  # Medium score (very large images)
                        elif width >= 1600 or height >= 800:
                            score = 2  # Lower score
                        elif width >= 800 or height >= 500:
                            score = 1  # Lowest score
                        elif width >= 500 or height >= 300:
                            score = 0  # Lowest score
                        else:
                            continue  # Skip small images
                
                image_urls.append({'url': img_src, 'score': score})
        
        # Sort images by score (highest first)
        sorted_images = sorted(image_urls, key=lambda x: x['score'], reverse=True)
        
        return sorted_images[:10]  # Ensure we don't return more than 10 images in total
    
    except Exception as e:
        logging.error(f"Error in get_relevant_images: {e}")
        return []

def parse_dimension(value: str) -> int:
    """Parse dimension value, handling px units"""
    if value.lower().endswith('px'):
        value = value[:-2]  # Remove 'px' suffix
    try:
        # Convert to float first to handle decimal values like '409.12'
        return int(float(value))
    except (ValueError, TypeError) as e:
        print(f"Error parsing dimension value {value}: {e}")
        return None

def extract_title(soup: BeautifulSoup) -> str:
    """Extract the title from the BeautifulSoup object"""
    return soup.title.string if soup.title else ""

def get_image_hash(image_url: str) -> str:
    """Calculate a simple hash based on the image filename and essential query parameters"""
    try:
        parsed_url = urlparse(image_url)
        
        # Extract the filename
        filename = parsed_url.path.split('/')[-1]
        
        # Extract essential query parameters (e.g., 'url' for CDN-served images)
        query_params = parse_qs(parsed_url.query)
        essential_params = query_params.get('url', [])
        
        # Combine filename and essential parameters
        image_identifier = filename + ''.join(essential_params)
        
        # Calculate hash
        return hashlib.md5(image_identifier.encode()).hexdigest()
    except Exception as e:
        logging.error(f"Error calculating image hash for {image_url}: {e}")
        return None


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """Clean the soup by removing unwanted tags"""
    for tag in soup.find_all(
        [
            "script",
            "style",
            "footer",
            "header",
            "nav",
            "menu",
            "sidebar",
            "svg",
        ]
    ):
        tag.decompose()

    disallowed_class_set = {"nav", "menu", "sidebar", "footer"}

    # clean tags with certain classes
    def does_tag_have_disallowed_class(elem) -> bool:
        if not isinstance(elem, bs4.Tag):
            return False

        return any(
            cls_name in disallowed_class_set for cls_name in elem.get("class", [])
        )

    for tag in soup.find_all(does_tag_have_disallowed_class):
        tag.decompose()

    return soup


def get_text_from_soup(soup: BeautifulSoup) -> str:
    """Get the relevant text from the soup with improved filtering"""
    text = soup.get_text(strip=True, separator="\n")
    # Remove excess whitespace
    text = re.sub(r"\s{2,}", " ", text)
    return text