from pydantic import BaseModel

from multimodal_ai.services.bus import Bus, Component
from multimodal_ai.services.types import Playback, Shutdown


class Ping(BaseModel):
    n: int


class Pong(BaseModel):
    n: int


def drain(inbox):
    items = []
    while not inbox.empty():
        items.append(inbox.get_nowait())
    return items


def test_routes_by_type_and_shutdown_reaches_everyone():
    bus = Bus()
    pings, both, other = (
        bus.subscribe(Ping),
        bus.subscribe(Ping, Pong),
        bus.subscribe(Playback),
    )
    bus.publish(Ping(n=1))
    bus.publish(Pong(n=2))
    bus.publish(Shutdown())
    assert [type(m) for m in drain(pings)] == [Ping, Shutdown]
    assert [type(m) for m in drain(both)] == [Ping, Pong, Shutdown]
    assert [type(m) for m in drain(other)] == [Shutdown]


def test_unsubscribed_messages_are_dropped():
    Bus().publish(Ping(n=1))  # no subscribers: nothing happens, no error


class Doubler(Component):
    consumes = (Ping,)

    def handle(self, msg: Ping) -> None:
        self.bus.publish(Pong(n=msg.n * 2))


class Crasher(Component):
    consumes = (Ping,)

    def handle(self, msg: Ping) -> None:
        raise RuntimeError("boom")


def test_component_transforms_until_shutdown():
    bus = Bus()
    out = bus.subscribe(Pong)
    worker = Doubler(bus, "doubler")
    worker.start()
    for n in range(3):
        bus.publish(Ping(n=n))
    bus.publish(Shutdown())
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert [m.n for m in drain(out) if isinstance(m, Pong)] == [0, 2, 4]


def test_crashing_component_shuts_everything_down():
    bus = Bus()
    watcher = bus.subscribe()  # receives only Shutdown
    worker = Crasher(bus, "crasher")
    worker.start()
    bus.publish(Ping(n=1))
    msg = watcher.get(timeout=2)
    assert isinstance(msg, Shutdown) and "crasher failed" in msg.reason
