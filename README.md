# Sloth FM

**Your GitHub inbox, read overnight by a sloth on your own laptop, and read back to you at breakfast.**

Sloth FM is a slow, private, open-weight night shift for developers. While you sleep, it works through your GitHub
notifications one at a time with **Gemma 3 running locally**, decides what needs you, what went well and what is
noise, and in the morning **Kokoro (an open-weight voice) reads you a short radio show** with a page of links.
Nothing leaves your machine: no API keys, no cloud model, no cost.

It is built to be slow on purpose. It works only when the laptop is plugged in, rests between notifications so the
fans stay quiet, and if the lid closes or the process is killed, it carries on from the next notification. That
durability comes from a **Temporal** workflow.

## Why

A month of my own GitHub notifications: 184 threads, most of them CI runs and bots. The few that mattered (a CLA to
sign, a reviewer waiting on me, a security advisory) were buried in the rest. Reading all of it is a chore; ignoring
all of it is how things get missed. Sloth FM does the reading so I do not have to.

## How it works

```
gh api notifications  ->  SQLite journal  ->  code decides the obvious  ->  Gemma 3 (local) judges the rest
                                                                                 |
     morning page + radio show (Kokoro, local)  <-  code writes every number  <--+
```

- **Code decides the obvious.** Passed or cancelled CI, releases you only watch, merged pull requests, and older runs
  of the same workflow on the same branch never reach the model.
- **Gemma judges the rest** with the facts a person would glance at: who opened it, its state, who spoke last, which
  branch a failing workflow ran on and whether that branch is yours. It returns a bucket, a reason and one spoken
  sentence, constrained by a JSON schema.
- **Code writes every number** in the show; the model only writes sentences, so counts are never hallucinated.
- **Private things stay private.** Security advisories and private repositories are never read aloud, and the
  `--public` page redacts them.
- **Temporal** runs the night: one activity per notification with retries, a durable timer that waits for the
  charger, a `wake` signal to start anyway, and a `progress` query.

## Run it

Requirements: macOS or Linux, Python 3.12+, [Ollama](https://ollama.com), the [Temporal CLI](https://temporal.io),
the GitHub CLI signed in (`gh auth login`), ffmpeg, and the Kokoro model files
(`kokoro-v1.0.onnx`, `voices-v1.0.bin`) in `~/.slothfm/kokoro`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ollama pull gemma3:4b
scripts/sloth.sh            # starts Ollama and Temporal if needed, then waits for the charger
scripts/sloth.sh --now      # or start right away
.venv/bin/python -m slothfm progress   # how far did it get?
.venv/bin/python -m slothfm wake       # on battery, but start anyway
.venv/bin/python -m slothfm morning    # rebuild this morning's page and show
open ~/.slothfm/mornings/$(date +%F)/index.html
```

Add `--tidy` to mark the noise as read on GitHub; it is the only action Sloth FM takes on your behalf.

## Open models

| Part | Model | Licence | Runs |
| --- | --- | --- | --- |
| Judgement | Gemma 3 4B (`gemma3:4b`) | Gemma Terms of Use | locally, through Ollama |
| Voice | Kokoro 82M (`bm_george`) | Apache-2.0 | locally, through kokoro-onnx |
| Durability | Temporal | MIT | locally, `temporal server start-dev` |

## License

MIT
