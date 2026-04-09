from __future__ import annotations

import argparse
import json
import socket
from dataclasses import asdict, dataclass
from typing import Callable

from goat_ai.config import Settings, load_settings

RuntimeTargetProbe = Callable[[str, int], tuple[bool, str]]


@dataclass(frozen=True)
class ResolvedRuntimeTarget:
    mode: str
    host: str
    port: int
    base_url: str
    reason: str


def can_bind_runtime_target(host: str, port: int) -> tuple[bool, str]:
    """Return whether the current environment can bind the requested host/port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError as exc:
        return False, str(exc)
    return True, "bind check passed"


def make_runtime_target(
    mode: str, host: str, port: int, reason: str
) -> ResolvedRuntimeTarget:
    return ResolvedRuntimeTarget(
        mode=mode,
        host=host,
        port=port,
        base_url=f"http://{host}:{port}",
        reason=reason,
    )


def ordered_runtime_targets(
    settings: Settings,
    *,
    host: str = "127.0.0.1",
    probe: RuntimeTargetProbe | None = None,
) -> list[ResolvedRuntimeTarget]:
    """Return deployment targets in preference order (single-port policy)."""
    bind_probe = probe or can_bind_runtime_target
    can_bind_server, reason = bind_probe(host, settings.server_port)
    if settings.deploy_target == "local":
        target_reason = (
            "GOAT_DEPLOY_TARGET=local is deprecated; enforcing server port policy"
        )
    elif settings.deploy_target == "server":
        target_reason = "GOAT_DEPLOY_TARGET explicitly set to server"
    elif can_bind_server:
        target_reason = "server port is bindable"
    else:
        target_reason = f"server port unavailable: {reason}"

    return [
        make_runtime_target("server62606", host, settings.server_port, target_reason)
    ]


def current_runtime_target(
    settings: Settings,
    *,
    current_port: int,
    host: str = "127.0.0.1",
) -> ResolvedRuntimeTarget:
    """Describe the currently active runtime target."""
    if current_port == settings.server_port:
        return make_runtime_target(
            "server62606", host, current_port, "current process bound to server port"
        )
    return make_runtime_target(
        "explicit_override", host, current_port, "current process bound to custom port"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve GOAT AI runtime target ports."
    )
    parser.add_argument(
        "--ordered-ports",
        action="store_true",
        help="Print target ports in preference order, one per line.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the resolved target list as JSON."
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = load_settings()
    targets = ordered_runtime_targets(settings)
    if args.ordered_ports:
        for target in targets:
            print(target.port)
        return
    if args.json:
        print(json.dumps([asdict(item) for item in targets], ensure_ascii=False))
        return
    print(targets[0].base_url)


if __name__ == "__main__":
    main()
