"""A tiny message bus, and a base class for thread-based components.

Each consumer *subscribes* to message types and gets its own inbox (a
queue.Queue). `publish(msg)` puts `msg` into every inbox subscribed to its
type. So:
- many producers can publish to the same consumer (they share its inbox);
- one message can reach many consumers (each inbox gets a reference);
- a message nobody subscribed to is simply dropped, so producers needn't
  know who, if anyone, is listening;
- an inbox can mix message types; its consumer checks `isinstance` to route.

queue.Queue is thread-safe, so publishing from any thread is fine.
"""

import queue
import sys
import threading
import traceback

from pydantic import BaseModel

from multimodal_ai.services.types import Shutdown


class Bus:
    def __init__(self) -> None:
        # (message types, inbox) pairs. Subscribe before starting threads.
        self._subscribers: list[tuple[tuple[type, ...], queue.Queue]] = []

    def subscribe(self, *types: type[BaseModel]) -> queue.Queue:
        """Return a new inbox receiving messages of `types`, and Shutdown."""
        inbox: queue.Queue = queue.Queue()
        self._subscribers.append(((*types, Shutdown), inbox))
        return inbox

    def publish(self, msg: BaseModel) -> None:
        for types, inbox in self._subscribers:
            if isinstance(msg, types):
                inbox.put(msg)


class Component(threading.Thread):
    """A thread that handles messages from its inbox until Shutdown.

    Subclasses list the message types they consume in `consumes`, implement
    `handle(msg)` (publishing results with `self.bus.publish`), and may
    override `setup()` to load models before the thread starts.
    """

    consumes: tuple[type[BaseModel], ...] = ()

    def __init__(self, bus: Bus, name: str) -> None:
        # daemon: don't keep the process alive if a thread is stuck in a
        # long model call when we exit.
        super().__init__(name=name, daemon=True)
        self.bus = bus
        self.inbox = bus.subscribe(*self.consumes)

    def setup(self) -> None:
        """Slow initialization (model loading). Called before start()."""

    def handle(self, msg: BaseModel) -> None:
        raise NotImplementedError

    def run(self) -> None:
        try:
            while not isinstance(msg := self.inbox.get(), Shutdown):
                self.handle(msg)
        except Exception as e:  # noqa: BLE001 - any crash: report, shut down
            self.fail(e)

    def fail(self, e: Exception) -> None:
        """Report a crash and stop the whole system, rather than hang."""
        traceback.print_exc(file=sys.stderr)
        self.bus.publish(Shutdown(reason=f"{self.name} failed: {e!r}"))
