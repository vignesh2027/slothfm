"""The night shift as a Temporal workflow: durable, slow and steady.

Each notification is one activity. If the laptop sleeps, the lid closes or the process is killed, the workflow
picks up at the next undecided notification. On battery it waits (a durable timer) instead of draining it.
This module stays free of I/O so it runs inside Temporal's deterministic sandbox; the work is in activities.py.
"""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy


@dataclass
class NightInput:
    days: int = 14
    pace_seconds: int = 3
    tidy: bool = False
    ignore_power: bool = False


@workflow.defn
class NightShift:
    def __init__(self):
        self.done, self.total, self.waiting_for_power, self.woken = 0, 0, False, False

    @workflow.signal
    def wake(self) -> None:
        """Poke the sloth: start now even on battery."""
        self.woken = True

    @workflow.query
    def progress(self) -> dict:
        return {"done": self.done, "total": self.total, "waiting_for_power": self.waiting_for_power}

    @workflow.run
    async def run(self, args: NightInput) -> dict:
        retry = RetryPolicy(initial_interval=timedelta(seconds=10), backoff_coefficient=2.0,
                            maximum_interval=timedelta(minutes=5), maximum_attempts=0)
        threads = await workflow.execute_activity("collect", args.days, start_to_close_timeout=timedelta(minutes=10),
                                                  retry_policy=retry)
        self.total = len(threads)
        buckets = {}
        for thread in threads:
            while not (args.ignore_power or self.woken) and not await workflow.execute_activity(
                    "plugged_in", start_to_close_timeout=timedelta(seconds=30), retry_policy=retry):
                self.waiting_for_power = True
                try:
                    await workflow.wait_condition(lambda: self.woken, timeout=timedelta(minutes=15))
                except TimeoutError:
                    pass
            self.waiting_for_power = False
            b = await workflow.execute_activity("triage_one", thread, start_to_close_timeout=timedelta(minutes=15),
                                                retry_policy=retry)
            buckets[b] = buckets.get(b, 0) + 1
            self.done += 1
            await workflow.sleep(timedelta(seconds=args.pace_seconds))
        page = await workflow.execute_activity("morning", args.tidy, start_to_close_timeout=timedelta(minutes=20),
                                               retry_policy=retry)
        return {"decided": self.done, "buckets": buckets, "page": page}
