import time
import socket
import requests
import itertools
import threading
import os

from PycePlus import __events__ as _EV
from PycePlus.CORE.timec import Time
from PycePlus.CORE.tools import asynchronous

_id_counter = itertools.count(1)
download_register = {}
_download_controls = {}

BUFFER_SIZE = 1024 * 1024

class DData:
    def __init__(self, id, url, data, path, total_time, size):
        self.id = id
        self.url = url
        self.data = data
        self.path = path
        self.time = total_time
        self.size = size

class DControl:
    def __init__(self, id):
        self.id = id
        self._pause_manual = threading.Event()
        self._pause_manual.set()
        self._pause_error = threading.Event()
        self._pause_error.set()
        self._cancel = threading.Event()
        self.thread = None

    def pause(self):
        self._pause_manual.clear()
        _EV.emit('network.client.paused', Time.current_ticks, self.id, "manual")

    def pause_for_error(self):
        self._pause_error.clear()
        _EV.emit('network.client.paused', Time.current_ticks, self.id, "error")

    def resume(self):
        self._pause_manual.set()
        _EV.emit('network.client.resume', Time.current_ticks, self.id, "manual")

    def resume_for_error(self):
        self._pause_error.set()
        _EV.emit('network.client.resume', Time.current_ticks, self.id, "error")

    def cancel(self):
        self._cancel.set()
        self._pause_manual.set()
        self._pause_error.set()
        _EV.emit('network.client.canceled', Time.current_ticks, self.id)

    def wait(self):
        if self.thread:
            self.thread.join()

    def get(self, wait=False):
        if wait:
            self.wait()
        return download_register.get(self.id)

    def wait_if_paused_or_canceled(self):
        while not (self._pause_manual.is_set() and self._pause_error.is_set()):
            if self._cancel.is_set():
                raise RuntimeError("Download canceled")
            time.sleep(0.01)
        if self._cancel.is_set():
            raise RuntimeError("Download canceled")

def is_connected(timeout=2.0):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False

def _resolve_output(url, output):
    if output:
        return os.path.abspath(output)
    name = url.split("/")[-1] or f"download_{next(_id_counter)}"
    return os.path.abspath(name)

def download(url, output=None):
    download_id = next(_id_counter)
    control = DControl(download_id)
    _download_controls[download_id] = control

    def _task():
        use_file = output is not None
        path = _resolve_output(url, output) if use_file else None
        data = bytearray() if not use_file else None

        try:
            start_time = time.time()
            try:
                r = requests.get(url, stream=True, timeout=60)
                r.raise_for_status()
            except requests.ConnectionError as e:
                control.pause_for_error()
                ddata = DData(download_id, url, None, path, 0, 0)
                _EV.emit('network.client.failed', Time.current_ticks, download_id, url, e, ddata)
                return
            except Exception as e:
                ddata = DData(download_id, url, None, path, 0, 0)
                _EV.emit('network.failed', Time.current_ticks, download_id, url, e, ddata)
                _download_controls.pop(download_id, None)
                return

            total_size = r.headers.get('content-length')
            total_size = int(total_size) if total_size else None
            _EV.emit('network.client.start', Time.current_ticks, download_id, url, total_size, path if use_file else '--memory--')

            f = open(path, "wb") if use_file else None
            downloaded = 0

            for chunk in r.iter_content(BUFFER_SIZE):
                control.wait_if_paused_or_canceled()
                if not chunk:
                    continue
                if use_file:
                    f.write(chunk)
                else:
                    data.extend(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                eta = (total_size - downloaded) / speed if total_size and speed > 0 else '--.--.--'
                _EV.emit('network.client.progress', Time.current_ticks, download_id, downloaded, elapsed, total_size, eta)

            total_time = time.time() - start_time
            ddata = DData(download_id, url, bytes(data) if data is not None else None, path, total_time, downloaded)
            download_register[download_id] = ddata
            _EV.emit('network.client.end', Time.current_ticks, ddata)

        except RuntimeError as e:
            _EV.emit('network.client.canceled', Time.current_ticks, download_id)
        except Exception as e:
            ddata = DData(download_id, url, bytes(data) if data is not None else None, path, time.time() - start_time, downloaded)
            _EV.emit('network.failed', Time.current_ticks, download_id, url, e, ddata)
        finally:
            if f:
                f.close()
            _download_controls.pop(download_id, None)

    t = asynchronous.Threads.run(_task, name='download')
    control.thread = t
    return control

# Métodos globales
def resume_for_errs():
    for c in _download_controls.values():
        if not c._pause_error.is_set() and not c._cancel.is_set():
            c.resume_for_error()

def resume_alls():
    for c in _download_controls.values():
        if not c._cancel.is_set():
            c.resume()
            c.resume_for_error()

def cancel_alls():
    for c in _download_controls.values():
        if not c._cancel.is_set():
            c.cancel()

def paused_alls():
    for c in _download_controls.values():
        if not c._cancel.is_set():
            c.pause()

def cancel_errs():
    for c in _download_controls.values():
        if not c._pause_error.is_set() and not c._cancel.is_set():
            c.cancel()