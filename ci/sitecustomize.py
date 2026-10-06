"""
Force Python networking to IPv4.

GitHub-hosted Linux runners can sometimes have an IPv6 route
that is unavailable to a dependency download server.

python-for-android uses Python urllib for some downloads.
This forces those Python network connections to IPv4.
"""

import socket


_original_getaddrinfo = socket.getaddrinfo


def ipv4_only_getaddrinfo(
    host,
    port,
    family=0,
    type=0,
    proto=0,
    flags=0,
):
    return _original_getaddrinfo(
        host,
        port,
        socket.AF_INET,
        type,
        proto,
        flags,
    )


socket.getaddrinfo = ipv4_only_getaddrinfo