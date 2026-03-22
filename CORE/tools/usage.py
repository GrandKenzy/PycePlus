import os
import psutil

_FACTORS = {
    'b': 1,
    'kb': 1024,
    'mb': 1024 ** 2,
    'gb': 1024 ** 3,
    'tb': 1024 ** 4,
    'pb': 1024 ** 5,
}

def _convert(value, fmt):
    return value / _FACTORS[fmt]

class Proc:
    pid = os.getpid()
    process = psutil.Process(pid)
    flag_mem = 0
    flag_disk = 0
    flag_mem_p = 0
    flag_disk_p = 0

def get_process_memory_usage(format: str='kb'):
    return _convert(Proc.process.memory_info().rss, format)

def get_process_disk_usage(format: str='gb'):
    io = Proc.process.io_counters()
    return _convert(io.read_bytes + io.write_bytes, format)

def get_memory_usage(format: str='kb'):
    m = psutil.virtual_memory()
    return _convert(m.total - m.available, format)

def get_disk_usage(format: str='kb'):
    d = psutil.disk_usage('/')
    return _convert(d.used, format)

def get_disk(format: str='kb'):
    return _convert(psutil.disk_usage('/').free, format)

def get_memory(format: str='kb'):
    return _convert(psutil.virtual_memory().available, format)

def memory_is_low(factor: float):
    m = psutil.virtual_memory()
    return m.available < m.total * factor

def disk_is_low(factor: float):
    d = psutil.disk_usage('/')
    return d.free < d.total * factor