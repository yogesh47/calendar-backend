import asyncio
from collections.abc import AsyncIterator

# Each open stream's queue, with the event loop it lives on. Routes that
# publish run in worker threads, and an asyncio.Queue is not thread-safe — so a
# message is handed to the queue's own loop instead of put on it directly.
_listeners: dict[str, set[asyncio.Queue]] = {}
_loops: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}


def subscribe(org_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _listeners.setdefault(org_id, set()).add(queue)
    _loops[queue] = asyncio.get_running_loop()

    return queue


def unsubscribe(org_id: str, queue: asyncio.Queue) -> None:
    listeners = _listeners.get(org_id)
    if listeners:
        listeners.discard(queue)
    _loops.pop(queue, None)


def publish(org_id: str, message: str) -> None:
    for queue in list(_listeners.get(org_id, set())):
        loop = _loops.get(queue)
        if loop and not loop.is_closed():
            loop.call_soon_threadsafe(queue.put_nowait, message)


async def stream(org_id: str, queue: asyncio.Queue) -> AsyncIterator[str]:
    yield "event: ready\ndata: connected\n\n"
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=20)
                yield f"event: calendar\ndata: {message}\n\n"
            except asyncio.TimeoutError:  # noqa: UP041 - on Python 3.10 this is not the builtin TimeoutError
                yield ": keep-alive\n\n"
    finally:
        unsubscribe(org_id, queue)
