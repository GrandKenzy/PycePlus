from typing import Any, Callable, Literal
import threading
from itertools import count

BLOCKS: dict[int, dict[str, Any]] = {
    0: {'name': 'system.start', 'calls': {}, 'lock': threading.Lock()},
    1: {'name': 'system.shutdown', 'calls': {}, 'lock': threading.Lock()},
    2: {'name': 'system.suspend', 'calls': {}, 'lock': threading.Lock()},
    3: {'name': 'system.resume', 'calls': {}, 'lock': threading.Lock()},
    4: {'name': 'system.error', 'calls': {}, 'lock': threading.Lock()},
    5: {'name': 'system.idle', 'calls': {}, 'lock': threading.Lock()},

    6: {'name': 'network.error', 'calls': {}, 'lock': threading.Lock()},
    7: {'name': 'network.connect', 'calls': {}, 'lock': threading.Lock()},
    8: {'name': 'network.disconnect', 'calls': {}, 'lock': threading.Lock()},
    9: {'name': 'network.receive', 'calls': {}, 'lock': threading.Lock()},
    10: {'name': 'network.send', 'calls': {}, 'lock': threading.Lock()},
    11: {'name': 'network.failed', 'calls': {}, 'lock': threading.Lock()},
    12: {'name': 'network.connectionError', 'calls': {}, 'lock': threading.Lock()},

    13: {'name': 'database.error', 'calls': {}, 'lock': threading.Lock()},
    14: {'name': 'database.connect', 'calls': {}, 'lock': threading.Lock()},
    15: {'name': 'database.disconnect', 'calls': {}, 'lock': threading.Lock()},
    16: {'name': 'database.receive', 'calls': {}, 'lock': threading.Lock()},
    17: {'name': 'database.send', 'calls': {}, 'lock': threading.Lock()},
    18: {'name': 'database.failed', 'calls': {}, 'lock': threading.Lock()},

    19: {'name': 'file.opened', 'calls': {}, 'lock': threading.Lock()},
    20: {'name': 'file.closed', 'calls': {}, 'lock': threading.Lock()},
    21: {'name': 'file.modified', 'calls': {}, 'lock': threading.Lock()},
    22: {'name': 'file.created', 'calls': {}, 'lock': threading.Lock()},
    23: {'name': 'file.deleted', 'calls': {}, 'lock': threading.Lock()},

    24: {'name': 'system.gui.fatigue', 'calls': {}, 'lock': threading.Lock()},
    
    25: {'name': 'memory.system.change', 'calls': {}, 'lock': threading.Lock()},
    26: {'name': 'memory.process.change', 'calls': {}, 'lock': threading.Lock()},
    27: {'name': 'memory.low', 'calls': {}, 'lock': threading.Lock()},

    28: {'name': 'disk.system.change', 'calls': {}, 'lock': threading.Lock()},
    29: {'name': 'disk.process.change', 'calls': {}, 'lock': threading.Lock()},
    30: {'name': 'disk.low', 'calls': {}, 'lock': threading.Lock()},
    
    31: {'name': 'thread.create', 'calls': {}, 'lock': threading.Lock()},
    32: {'name': 'thread.start', 'calls': {}, 'lock': threading.Lock()},
    33: {'name': 'thread.end', 'calls': {}, 'lock': threading.Lock()},
    34: {'name': 'thread.error', 'calls': {}, 'lock': threading.Lock()},

    35: {'name': 'network.client.start', 'calls': {}, 'lock': threading.Lock()},
    36: {'name': 'network.client.progress', 'calls': {}, 'lock': threading.Lock()},
    37: {'name': 'network.client.end', 'calls': {}, 'lock': threading.Lock()},
    38: {'name': 'network.client.paused', 'calls': {}, 'lock': threading.Lock()},
    39: {'name': 'network.client.resume', 'calls': {}, 'lock': threading.Lock()},
    40: {'name': 'network.client.canceled', 'calls': {}, 'lock': threading.Lock()},
    41: {'name': 'network.reconnect', 'calls': {}, 'lock': threading.Lock()},
    42: {'name': 'system.window.lost', 'calls': {}, 'lock': threading.Lock()},
    43: {'name': 'system.window.gained', 'calls': {}, 'lock': threading.Lock()}
}

CORE_EVENTS = Literal[
    'system.start','system.shutdown','system.suspend','system.resume','system.error','system.idle',

    'network.error','network.connect','network.disconnect','network.receive','network.send','network.failed','network.connectionError',

    'database.error','database.connect','database.disconnect','database.receive','database.send','database.failed',

    'file.opened','file.closed','file.modified','file.created','file.deleted',

    'system.gui.fatigue',

    'memory.system.change','memory.process.change','memory.low',
    'disk.system.change','disk.process.change','disk.low',
    
    'thread.create','thread.start','thread.end','thread.error',

    'network.client.start','network.client.progress','network.client.end',
    'network.client.paused','network.client.resume', 'network.client.canceled', 'network.reconnect',
    'system.window.lost', 'system.window.gained'
]

_NAME_TO_ID = {v['name']: k for k, v in BLOCKS.items()}
_id_gen = count()


def _get_id(event: str | int) -> int:
    return event if isinstance(event, int) else _NAME_TO_ID[event]


def emit(event: CORE_EVENTS | int, *args: Any, **kwargs: Any):
    eid = _get_id(event)
    block = BLOCKS[eid]
    with block['lock']:
        calls = tuple(block['calls'].values())
    for fn in calls:
        try:
            fn(*args, **kwargs)
        except Exception as e:
            if eid != _NAME_TO_ID['system.error']:
                emit('system.error', e)


def register_event(event: CORE_EVENTS | int, on_event: Callable[..., None]) -> int:
    eid = _get_id(event)
    block = BLOCKS[eid]
    cid = next(_id_gen)
    with block['lock']:
        block['calls'][cid] = on_event
    return cid


def unregister_event(event: CORE_EVENTS | int, on_event: Callable[..., None]):
    eid = _get_id(event)
    block = BLOCKS[eid]
    with block['lock']:
        calls = block['calls']
        for k, v in list(calls.items()):
            if v == on_event:
                del calls[k]
                break


def unregister_by_index(event: CORE_EVENTS | int, index: int):
    eid = _get_id(event)
    block = BLOCKS[eid]
    with block['lock']:
        block['calls'].pop(index, None)


def clear_block(event: CORE_EVENTS | int):
    eid = _get_id(event)
    block = BLOCKS[eid]
    with block['lock']:
        block['calls'].clear()