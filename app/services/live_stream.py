import asyncio
from typing import AsyncIterator

_listeners: dict[str, set[asyncio.Queue]] = {}


def subscribe(org_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _listeners.setdefault(org_id, set()).add(queue)

    return queue


def unsubscribe(org_id: str, queue: asyncio.Queue) -> None:
    listeners = _listeners.get(org_id)
    if listeners:
        listeners.discard(queue)


def publish(org_id: str, message: str) -> None:
    for queue in list(_listeners.get(org_id, set())):
        queue.put_nowait(message)


async def stream(org_id: str, queue: asyncio.Queue) -> AsyncIterator[str]:
    yield "event: ready\ndata: connected\n\n"
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=20)
                yield f"event: calendar\ndata: {message}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    finally:
        unsubscribe(org_id, queue)
