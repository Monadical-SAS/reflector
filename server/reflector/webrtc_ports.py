"""
Monkey-patch aioice to use a fixed UDP port range for ICE candidates,
and optionally rewrite SDP to advertise a different host IP.

This allows running the server in Docker with bridge networking
(no network_mode: host) by:
  1. Restricting ICE UDP ports to a known range that can be mapped in Docker
  2. Replacing container-internal IPs with the Docker host IP in SDP answers
"""

import asyncio
import socket

from reflector.logger import logger


def parse_port_range(range_str: str) -> tuple[int, int]:
    """Parse a 'min-max' string into (min_port, max_port)."""
    parts = range_str.split("-")
    if len(parts) != 2:
        raise ValueError(
            f"WEBRTC_PORT_RANGE must be 'min-max', got: {range_str!r}"
        )
    min_port, max_port = int(parts[0]), int(parts[1])
    if not (1024 <= min_port <= max_port <= 65535):
        raise ValueError(
            f"Invalid port range: {min_port}-{max_port} "
            "(must be 1024-65535 with min <= max)"
        )
    return min_port, max_port


def patch_aioice_port_range(min_port: int, max_port: int) -> None:
    """
    Monkey-patch aioice so that ICE candidate UDP sockets bind to ports
    within [min_port, max_port] instead of OS-assigned ephemeral ports.

    Works by temporarily wrapping loop.create_datagram_endpoint() during
    aioice's get_component_candidates() to intercept bind(addr, 0) calls.
    """
    import aioice.ice as _ice

    _original = _ice.Connection.get_component_candidates
    _state = {"next_port": min_port}

    async def _patched_get_component_candidates(
        self, component, addresses, timeout=5
    ):
        loop = asyncio.get_event_loop()
        _orig_create = loop.create_datagram_endpoint

        async def _create_with_port_range(*args, **kwargs):
            local_addr = kwargs.get("local_addr")
            if local_addr and local_addr[1] == 0:
                addr = local_addr[0]
                # Try each port in the range (wrapping around)
                attempts = max_port - min_port + 1
                for _ in range(attempts):
                    port = _state["next_port"]
                    _state["next_port"] = (
                        min_port
                        if _state["next_port"] >= max_port
                        else _state["next_port"] + 1
                    )
                    try:
                        kwargs["local_addr"] = (addr, port)
                        return await _orig_create(*args, **kwargs)
                    except OSError:
                        continue
                # All ports exhausted, fall back to OS assignment
                logger.warning(
                    "All WebRTC ports in range exhausted, falling back to OS",
                    min_port=min_port,
                    max_port=max_port,
                )
                kwargs["local_addr"] = (addr, 0)
            return await _orig_create(*args, **kwargs)

        loop.create_datagram_endpoint = _create_with_port_range
        try:
            return await _original(self, component, addresses, timeout)
        finally:
            loop.create_datagram_endpoint = _orig_create

    _ice.Connection.get_component_candidates = _patched_get_component_candidates
    logger.info(
        "aioice patched for WebRTC port range",
        min_port=min_port,
        max_port=max_port,
    )


def resolve_webrtc_host(host: str) -> str:
    """Resolve a hostname or IP to an IP address for ICE candidate rewriting."""
    try:
        ip = socket.gethostbyname(host)
        logger.info("Resolved WEBRTC_HOST", host=host, ip=ip)
        return ip
    except socket.gaierror:
        logger.warning("Could not resolve WEBRTC_HOST, using as-is", host=host)
        return host


def rewrite_sdp_host(sdp: str, target_ip: str) -> str:
    """
    Replace container-internal IPs in SDP with target_ip so that
    ICE candidates advertise a routable address.
    """
    import aioice.ice

    container_ips = aioice.ice.get_host_addresses(use_ipv4=True, use_ipv6=False)
    for ip in container_ips:
        if ip != "127.0.0.1" and ip != target_ip:
            sdp = sdp.replace(ip, target_ip)
    return sdp
