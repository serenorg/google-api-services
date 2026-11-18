# ABOUTME: Fetches bounded public HTTP pages without loading embedded resources.
# ABOUTME: Validates every redirect and pins connections to checked public addresses.

import asyncio
import base64
import ipaddress
import socket
import ssl

import httpcore
import httpx


class UnsafeURL(ValueError):
    """The URL could reach a non-public destination."""


async def _public_address(url: httpx.URL) -> str:
    if url.scheme not in ("http", "https") or not url.host or url.userinfo:
        raise UnsafeURL("Only public HTTP(S) URLs without credentials are allowed")
    host = url.host.rstrip(".").lower()
    if host == "metadata.google.internal" or "%" in host:
        raise UnsafeURL("Private and metadata destinations are refused")
    try:
        records = await asyncio.get_running_loop().getaddrinfo(
            host, url.port or (443 if url.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeURL("Destination could not be resolved") from exc
    if not records:
        raise UnsafeURL("Destination could not be resolved")
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if isinstance(address, ipaddress.IPv6Address) and (
            address.sixtofour or address.teredo
            or address in ipaddress.ip_network("64:ff9b::/96")
        ):
            raise UnsafeURL("Address translation destinations are refused")
        if not address.is_global or address.is_multicast:
            raise UnsafeURL("Private and metadata destinations are refused")
    return records[0][4][0]


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    """Connect to a checked IP while retaining the URL's Host and TLS identity."""

    def __init__(self, address: str, proxy: str | None):
        self.address = address
        self.backend = httpcore.AnyIOBackend()
        self.proxy = httpx.Proxy(proxy) if proxy else None
        if self.proxy and self.proxy.url.scheme not in ("http", "https"):
            raise ValueError("Only HTTP(S) proxies are supported")

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        options = dict(timeout=timeout, local_address=local_address, socket_options=socket_options)
        if self.proxy is None:
            return await self.backend.connect_tcp(self.address, port, **options)

        # CONNECT to the checked IP, so a proxy cannot resolve the target again.
        proxy_url = self.proxy.url
        stream = await self.backend.connect_tcp(
            proxy_url.host, proxy_url.port or (443 if proxy_url.scheme == "https" else 80),
            **options,
        )
        try:
            if proxy_url.scheme == "https":
                stream = await stream.start_tls(
                    ssl.create_default_context(), server_hostname=proxy_url.host, timeout=timeout,
                )
            authority = f"[{self.address}]:{port}" if ":" in self.address else f"{self.address}:{port}"
            headers = f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n"
            if self.proxy.raw_auth:
                credentials = base64.b64encode(b":".join(self.proxy.raw_auth)).decode("ascii")
                headers += f"Proxy-Authorization: Basic {credentials}\r\n"
            await stream.write((headers + "\r\n").encode("ascii"), timeout=timeout)
            reply = bytearray()
            while b"\r\n\r\n" not in reply:
                chunk = await stream.read(1, timeout=timeout)
                if not chunk or len(reply) >= 16_384:
                    raise httpcore.ProxyError("Invalid proxy CONNECT response")
                reply.extend(chunk)
            if bytes(reply).split(b"\r\n", 1)[0].split()[1:2] != [b"200"]:
                raise httpcore.ProxyError("Proxy CONNECT refused")
            return stream
        except BaseException:
            await stream.aclose()
            raise

    async def sleep(self, seconds):
        await self.backend.sleep(seconds)


class _PinnedTransport(httpx.AsyncHTTPTransport):
    def __init__(self, address: str, proxy: str | None):
        super().__init__(trust_env=False)
        self._pool = httpcore.AsyncConnectionPool(network_backend=_PinnedBackend(address, proxy))


async def fetch(url, *, proxy=None, max_bytes=5_000_000, timeout=20, on_bytes=None) -> httpx.Response:
    """Fetch one public page, following at most five checked redirects.

    Returns a buffered httpx.Response, retaining the final URL, headers and cookies.
    Unsafe destinations and oversized bodies raise ValueError; HTTP errors retain
    httpx's HTTPStatusError. The timeout bounds the whole fetch, including DNS.
    on_bytes receives each downloaded body chunk size, including redirects and errors.
    Explicit HTTP(S) proxies use CONNECT to the validated IP for both URL schemes.
    """
    if max_bytes < 0 or timeout <= 0:
        raise ValueError("max_bytes must be nonnegative and timeout must be positive")
    current = httpx.URL(url)
    async with asyncio.timeout(timeout):
        for redirects in range(6):
            address = await _public_address(current)
            async with httpx.AsyncClient(
                transport=_PinnedTransport(address, proxy), trust_env=False,
                follow_redirects=False, timeout=timeout,
                headers={"Accept-Encoding": "identity"},
            ) as client:
                async with client.stream("GET", current) as response:
                    content = bytearray()
                    async for chunk in response.aiter_raw():
                        if on_bytes is not None:
                            on_bytes(len(chunk))
                        if len(content) + len(chunk) > max_bytes:
                            raise ValueError("Response exceeds max_bytes")
                        content.extend(chunk)
                    # Constructing a Response with content decodes it immediately.
                    # Refuse encodings first, including on redirects and errors.
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        if response.status_code in (403, 429):
                            response.raise_for_status()
                        raise ValueError("Compressed responses are refused to enforce the byte limit")
                    buffered = httpx.Response(
                        response.status_code, headers=response.headers, content=bytes(content),
                        request=response.request,
                    )
                    if response.is_redirect:
                        if redirects == 5:
                            raise httpx.TooManyRedirects("More than five redirects", request=response.request)
                        current = current.join(response.headers["location"])
                        continue
                    buffered.raise_for_status()
                    return buffered
    raise AssertionError("Unreachable redirect state")
