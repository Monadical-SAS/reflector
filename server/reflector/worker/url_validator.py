"""
URL validation for preventing SSRF attacks
"""
import ipaddress
import re
from urllib.parse import urlparse
from typing import Optional, Set

from reflector.logger import logger
from reflector.settings import settings


# Default allowed domains for audio downloads
DEFAULT_ALLOWED_DOMAINS = {
    "s3.amazonaws.com",
    "s3-us-west-1.amazonaws.com", 
    "s3-us-west-2.amazonaws.com",
    "s3-us-east-1.amazonaws.com",
    "s3-us-east-2.amazonaws.com",
    "s3-eu-west-1.amazonaws.com",
    "s3-eu-central-1.amazonaws.com",
    "s3-ap-southeast-1.amazonaws.com",
    "s3-ap-southeast-2.amazonaws.com",
    "s3-ap-northeast-1.amazonaws.com",
    # Add CloudFront domains if needed
}

# Private IP ranges that should be blocked
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

# Maximum file size (500MB by default)
MAX_FILE_SIZE = getattr(settings, "MAX_AUDIO_FILE_SIZE", 500 * 1024 * 1024)


def get_allowed_domains() -> Set[str]:
    """Get the set of allowed domains from settings or use defaults"""
    custom_domains = getattr(settings, "ALLOWED_AUDIO_DOMAINS", [])
    allowed = DEFAULT_ALLOWED_DOMAINS.copy()
    if custom_domains:
        allowed.update(custom_domains)
    return allowed


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP address"""
    try:
        # Check if it's already an IP address
        ip = ipaddress.ip_address(hostname)
        for private_range in PRIVATE_IP_RANGES:
            if ip in private_range:
                return True
        return False
    except ValueError:
        # Not an IP address, would need DNS resolution
        # For now, we'll allow it if it's a hostname
        # In production, you might want to resolve and check
        return False


def validate_audio_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate an audio URL for security.
    
    Returns:
        (is_valid, error_message)
    """
    # Check for empty URL
    if not url:
        return False, "URL cannot be empty"
    
    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"
    
    # Check protocol
    if parsed.scheme not in ("http", "https", "s3"):
        return False, f"Unsupported protocol: {parsed.scheme}"
    
    # S3 URLs are always allowed (they use AWS credentials)
    if parsed.scheme == "s3":
        return True, None
    
    # Check hostname exists
    if not parsed.hostname:
        return False, "URL must have a hostname"
    
    # Check for private IPs
    if is_private_ip(parsed.hostname):
        return False, "Access to private IP addresses is not allowed"
    
    # Check against allowed domains
    allowed_domains = get_allowed_domains()
    
    # Check if hostname matches any allowed domain
    hostname = parsed.hostname.lower()
    is_allowed = False
    
    for allowed_domain in allowed_domains:
        if hostname == allowed_domain or hostname.endswith(f".{allowed_domain}"):
            is_allowed = True
            break
    
    # Also check for S3 bucket patterns
    if not is_allowed:
        # Match patterns like bucket-name.s3.region.amazonaws.com
        s3_pattern = re.compile(r'^[\w\-]+\.s3[\.\-][\w\-]+\.amazonaws\.com$')
        if s3_pattern.match(hostname):
            is_allowed = True
    
    if not is_allowed:
        return False, f"Domain '{hostname}' is not in the allowed list"
    
    # URL is valid
    return True, None


async def check_file_size(url: str, session) -> tuple[bool, Optional[str]]:
    """
    Check file size via HEAD request.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        async with session.head(url, allow_redirects=True, timeout=10) as response:
            # Check Content-Length header
            content_length = response.headers.get('Content-Length')
            if content_length:
                size = int(content_length)
                if size > MAX_FILE_SIZE:
                    size_mb = size / (1024 * 1024)
                    max_mb = MAX_FILE_SIZE / (1024 * 1024)
                    return False, f"File too large: {size_mb:.1f}MB exceeds maximum of {max_mb:.1f}MB"
            
            # Check Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if content_type:
                # Allow audio/* and video/* types
                if not (content_type.startswith('audio/') or 
                        content_type.startswith('video/') or
                        content_type == 'application/octet-stream'):
                    return False, f"Invalid content type: {content_type}"
            
            return True, None
            
    except Exception as e:
        # If HEAD fails, we'll still allow the download but log the warning
        logger.warning(f"Failed to check file size for {url}: {e}")
        return True, None