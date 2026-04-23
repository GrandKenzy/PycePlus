from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PycePlus import __events__ as _EV
from PycePlus.CORE.tools.asynchronous import Threads as asynchronous


@dataclass(slots=True)
class DownloadResult:
    url: str
    path: str | None = None
    data: bytes = b""
    status: int | None = None
    headers: dict[str, str] | None = None
    error: BaseException | None = None

    _done: object = field(default_factory=lambda: __import__("threading").Event(), init=False, repr=False, compare=False)
    _thread: object | None = field(default=None, init=False, repr=False, compare=False)

    def wait(self, timeout: float | None = None) -> "DownloadResult":
        if not self._done.wait(timeout):
            raise TimeoutError("Download not finished before timeout.")
        if self.error is not None:
            raise self.error
        return self

    def get(self, wait: bool = True) -> "DownloadResult":
        return self.wait() if wait else self

    @property
    def done(self) -> bool:
        return self._done.is_set()

    @property
    def ok(self) -> bool:
        return self.done and self.error is None and (self.status is None or 200 <= self.status < 400)

    @property
    def content_length(self) -> int | None:
        if not self.headers:
            return None
        value = self.headers.get("Content-Length")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def content_type(self) -> str | None:
        if not self.headers:
            return None
        return self.headers.get("Content-Type")


def is_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _filename_from_url(url: str) -> str:
    name = Path(urlsplit(url).path).name
    return name or "download.bin"


def _resolve_path(url: str, path: str | os.PathLike[str] | None) -> Path | None:
    if path is None:
        return None

    p = Path(path)
    path_str = str(path)

    if (p.exists() and p.is_dir()) or path_str.endswith(("/", "\\")):
        p = p / _filename_from_url(url)

    return p


def _download_into(
    result: DownloadResult,
    save_path: Path | None,
    timeout: float,
) -> DownloadResult:
    url = result.url
    response = None

    _EV.emit("network.client.start", url, True)

    try:
        request = Request(
            url,
            headers={
                "User-Agent": "PycePlus/3.0",
                "Accept": "*/*",
                "Connection": "close",
            },
        )

        response = urlopen(request, timeout=timeout)
        _EV.emit("network.connect", url)

        result.status = getattr(response, "status", None)
        result.headers = dict(response.headers.items())

        total = result.content_length
        chunks: list[bytes] = []
        downloaded = 0

        while True:
            chunk = response.read(64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            downloaded += len(chunk)
            _EV.emit("network.client.progress", url, downloaded, total)

        result.data = b"".join(chunks)

        if save_path is not None:
            existed = save_path.exists()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(result.data)
            result.path = str(save_path)
            _EV.emit("file.modified" if existed else "file.created", result.path)

        _EV.emit("network.client.end", url, True, result.status, len(result.data), result.path)
        return result

    except BaseException as exc:
        result.error = exc
        _EV.emit("network.error", url, exc)
        _EV.emit("network.failed", url, exc)
        _EV.emit("network.client.end", url, False, result.status, len(result.data), result.path)
        raise

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

        _EV.emit("network.disconnect", url)
        result._done.set()


def download(
    url: str,
    path: str | os.PathLike[str] | None = None,
    timeout: float = 15.0,
    asynchronous_mode: bool = False,
) -> DownloadResult:
    result = DownloadResult(url=url)
    save_path = _resolve_path(url, path)

    if asynchronous_mode:
        def _task():
            return _download_into(result, save_path, timeout)

        result._thread = asynchronous.run(_task, name=f"download:{_filename_from_url(url)}")
        return result

    return _download_into(result, save_path, timeout)