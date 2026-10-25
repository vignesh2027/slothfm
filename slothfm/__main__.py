"""sloth-fm: night | morning | status | tidy

  python -m slothfm night            # start (or resume) tonight's shift; Ctrl-C any time, run again to resume
  python -m slothfm night --now      # do not wait for the charger
  python -m slothfm morning          # rebuild the page and the show from what was decided
  python -m slothfm morning --public # same, with private items redacted, for sharing
  python -m slothfm progress         # ask the running shift how far it got (a Temporal query)
  python -m slothfm wake             # start now even on battery (a Temporal signal)
  python -m slothfm status
"""
import argparse
import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from . import config, store


async def night(args):
    from temporalio.client import Client
    from temporalio.exceptions import WorkflowAlreadyStartedError
    from temporalio.worker import Worker

    from .activities import collect, morning, plugged_in, triage_one
    from .workflows import NightInput, NightShift
    client = await Client.connect("localhost:7233")
    wid = f"night-{datetime.now():%Y-%m-%d}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        async with Worker(client, task_queue=config.TASK_QUEUE, workflows=[NightShift],
                          activities=[collect, plugged_in, triage_one, morning], activity_executor=pool):
            try:
                handle = await client.start_workflow(
                    NightShift.run, NightInput(days=args.days, tidy=args.tidy, ignore_power=args.now,
                                               pace_seconds=args.pace),
                    id=wid, task_queue=config.TASK_QUEUE)
                print(f"night shift {wid} started")
            except WorkflowAlreadyStartedError:
                handle = client.get_workflow_handle(wid)
                print(f"night shift {wid} already running; resuming it")
            result = await handle.result()
            print(json.dumps(result, indent=2))


async def poke(signal):
    from temporalio.client import Client

    from .workflows import NightShift
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(f"night-{datetime.now():%Y-%m-%d}")
    if signal:
        await handle.signal(NightShift.wake)
        print("poked the sloth: working now, even on battery")
    from temporalio.service import RPCError
    try:
        print(json.dumps(await handle.query(NightShift.progress)))
    except RPCError as e:
        print(f"the night shift is saved but no worker is running ({e.message}); run scripts/sloth.sh to resume")


def status():
    con = store.db()
    rows = con.execute("SELECT bucket, decided_by, COUNT(*) n FROM items GROUP BY bucket, decided_by").fetchall()
    for r in rows:
        print(f"{r['bucket'] or 'pending':<10} {r['decided_by'] or '':<6} {r['n']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="slothfm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("night")
    n.add_argument("--now", action="store_true", help="work even on battery")
    n.add_argument("--tidy", action="store_true", help="mark noise as read on GitHub")
    n.add_argument("--days", type=int, default=config.DAYS)
    n.add_argument("--pace", type=int, default=config.PACE_SECONDS)
    m = sub.add_parser("morning")
    m.add_argument("--tidy", action="store_true")
    m.add_argument("--public", action="store_true")
    sub.add_parser("status")
    sub.add_parser("progress")
    sub.add_parser("wake")
    a = ap.parse_args(argv)
    if a.cmd == "night":
        asyncio.run(night(a))
    elif a.cmd == "morning":
        from .morning import make
        print(make(tidy=a.tidy, public=a.public))
    elif a.cmd in ("progress", "wake"):
        asyncio.run(poke(a.cmd == "wake"))
    else:
        status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
