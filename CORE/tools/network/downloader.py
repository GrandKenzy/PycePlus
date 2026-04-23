from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

@dataclass(slots=True)
class DownloadResult:
    url: str
    path: str | None
    data: bytes
    status: int | None = None
    headers: dict[str, str] | None = None

    def get(self, _sync: bool = True) -> "DownloadResult":
        return self


def is_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def download(url: str, path: str | os.PathLike[str] | None = None, timeout: float = 15.0) -> DownloadResult:
    request = Request(url, headers={"User-Agent": "PycePlus/3.0"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read()
        headers = dict(response.headers.items())
        status = getattr(response, "status", None)

    file_path: str | None = None
    if path is not None:
        p = Path(path)
        if p.is_dir():
            p = p / Path(url).name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        file_path = str(p)

    return DownloadResult(url=url, path=file_path, data=data, status=status, headers=headers)