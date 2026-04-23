from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from PycePlus import __events__ as _EV
from PycePlus.CORE.timec import Time
from PycePlus.CORE.tasker import GLOBAL_TASKER as _TASKER


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": True, "data": value.hex()}
    raise TypeError(f"Unsupported type: {type(value)!r}")


def _pack(message: Any) -> bytes:
    return (json.dumps(message, ensure_ascii=False, default=_json_default) + "\n").encode("utf-8")


def _unpack(line: bytes) -> Any:
    payload = json.loads(line.decode("utf-8"))
    if isinstance(payload, dict) and payload.get("__bytes__"):
        return bytes.fromhex(payload["data"])
    return payload


@dataclass(slots=True)
class PeerInfo:
    id: int
    address: tuple[str, int]
    socket: socket.socket = field(repr=False)


class HostServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        on_connect: Callable[[PeerInfo], Any] | None = None,
        on_message: Callable[[PeerInfo, Any], Any] | None = None,
        on_disconnect: Callable[[PeerInfo], Any] | None = None,
        on_error: Callable[[BaseException], Any] | None = None,
        backlog: int = 16,
    ):
        self.host = host
        self.port = port
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        self.backlog = backlog
        self._sock: socket.socket | None = None
        self._alive = False
        self._lock = threading.RLock()
        self._next_id = 1
        self.clients: dict[int, PeerInfo] = {}
        self.thread: threading.Thread | None = None

    def start(self) -> "HostServer":
        if self._alive:
            return self
        self._alive = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(self.backlog)
        self.thread = threading.Thread(target=self._accept_loop, daemon=True, name=f"PycePlusServer:{self.port}")
        self.thread.start()
        return self

    def stop(self) -> None:
        self._alive = False
        with self._lock:
            for peer in list(self.clients.values()):
                try:
                    peer.socket.close()
                except Exception:
                    pass
            self.clients.clear()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def broadcast(self, message: Any) -> None:
        for peer in list(self.clients.values()):
            self.send(peer.id, message)

    def send(self, peer_id: int, message: Any) -> None:
        peer = self.clients.get(peer_id)
        if not peer:
            return
        try:
            peer.socket.sendall(_pack(message))
            _EV.emit("network.send", Time.current_ticks, peer_id, message)
        except Exception as exc:
            self._emit_error(exc)

    def _emit_error(self, exc: BaseException) -> None:
        _EV.emit("network.error", Time.current_ticks, exc)
        if self.on_error:
            _TASKER.call_soon(self.on_error, exc)

    def _accept_loop(self) -> None:
        assert self._sock is not None
        while self._alive:
            try:
                client, address = self._sock.accept()
            except OSError:
                break
            except BaseException as exc:
                self._emit_error(exc)
                continue

            with self._lock:
                peer = PeerInfo(self._next_id, address, client)
                self._next_id += 1
                self.clients[peer.id] = peer

            _EV.emit("network.connect", Time.current_ticks, peer.id, address)
            if self.on_connect:
                _TASKER.call_soon(self.on_connect, peer)

            threading.Thread(target=self._client_loop, args=(peer,), daemon=True, name=f"PycePlusPeer:{peer.id}").start()

    def _client_loop(self, peer: PeerInfo) -> None:
        sock = peer.socket
        try:
            file = sock.makefile("rb")
            while self._alive:
                line = file.readline()
                if not line:
                    break
                try:
                    message = _unpack(line)
                except Exception as exc:
                    self._emit_error(exc)
                    continue
                _EV.emit("network.receive", Time.current_ticks, peer.id, message)
                if self.on_message:
                    _TASKER.call_soon(self.on_message, peer, message)
        except BaseException as exc:
            self._emit_error(exc)
        finally:
            with self._lock:
                self.clients.pop(peer.id, None)
            try:
                sock.close()
            except Exception:
                pass
            _EV.emit("network.disconnect", Time.current_ticks, peer.id, peer.address)
            if self.on_disconnect:
                _TASKER.call_soon(self.on_disconnect, peer)


class HostClient:
    def __init__(
        self,
        host: str,
        port: int,
        on_connect: Callable[["HostClient"], Any] | None = None,
        on_message: Callable[["HostClient", Any], Any] | None = None,
        on_disconnect: Callable[["HostClient"], Any] | None = None,
        on_error: Callable[[BaseException], Any] | None = None,
        timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.on_connect = on_connect
        self.on_message = on_message
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        self.timeout = timeout
        self.socket: socket.socket | None = None
        self._alive = False
        self.thread: threading.Thread | None = None

    @property
    def connected(self) -> bool:
        return self._alive and self.socket is not None

    def connect(self) -> "HostClient":
        if self._alive:
            return self
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(None)
        self._alive = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name=f"PycePlusClient:{self.host}:{self.port}")
        self.thread.start()
        _EV.emit("network.connect", Time.current_ticks, (self.host, self.port))
        if self.on_connect:
            _TASKER.call_soon(self.on_connect, self)
        return self

    def send(self, message: Any) -> None:
        if not self.socket:
            raise ConnectionError("Client is not connected")
        self.socket.sendall(_pack(message))
        _EV.emit("network.send", Time.current_ticks, message)

    def close(self) -> None:
        self._alive = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def _emit_error(self, exc: BaseException) -> None:
        _EV.emit("network.error", Time.current_ticks, exc)
        if self.on_error:
            _TASKER.call_soon(self.on_error, exc)

    def _loop(self) -> None:
        assert self.socket is not None
        try:
            file = self.socket.makefile("rb")
            while self._alive:
                line = file.readline()
                if not line:
                    break
                try:
                    message = _unpack(line)
                except Exception as exc:
                    self._emit_error(exc)
                    continue
                _EV.emit("network.receive", Time.current_ticks, message)
                if self.on_message:
                    _TASKER.call_soon(self.on_message, self, message)
        except BaseException as exc:
            self._emit_error(exc)
        finally:
            self._alive = False
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            _EV.emit("network.disconnect", Time.current_ticks, (self.host, self.port))
            if self.on_disconnect:
                _TASKER.call_soon(self.on_disconnect, self)
