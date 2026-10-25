"""The morning show: code writes every number, Gemma wrote each sentence, Kokoro reads it aloud."""
import subprocess
from collections import Counter
from pathlib import Path

from . import config

ORDINALS = ["First", "Next", "Then", "Also", "And", "One more"]


def noise_summary(items):
    kinds = Counter()
    for it in items:
        if it["type"] == "CheckSuite":
            kinds["CI runs that need nothing from you"] += 1
        elif it["type"] == "Release":
            kinds["releases from repositories you watch"] += 1
        else:
            kinds["threads you were only following"] += 1
    return ", ".join(f"{n} {k}" for k, n in kinds.most_common(3))


def script(items, thought, tidied, me=""):
    from .brain import tidy_speech
    needs_all = [i for i in items if i["bucket"] == "needs_you"]
    needs = [i for i in needs_all if i.get("urgency") == "today"]
    later = [i for i in needs_all if i.get("urgency") != "today"]
    good = [i for i in items if i["bucket"] == "good_news"]
    noise = [i for i in items if i["bucket"] == "noise"]
    total = len(items)
    lines = [f"Good morning. This is Sloth FM. While you slept, I read {total} GitHub notifications, slowly, "
             f"on your own laptop, so you would not have to."]
    if needs:
        lines.append(f"{len(needs)} {'thing needs' if len(needs) == 1 else 'things need'} you today.")
        for n, it in enumerate(needs[:6]):
            say = tidy_speech(it["say"], me) if it["say"] else f"{it['why']}, in {it['repo'].split('/')[-1]}."
            lines.append(f"{ORDINALS[min(n, len(ORDINALS) - 1)]}: {say}")
        if len(needs) > 6:
            lines.append(f"There are {len(needs) - 6} more urgent ones on your morning page.")
    else:
        lines.append("Nothing needs you today. Truly nothing.")
    if later:
        lines.append(f"{len(later)} more are yours this week, but nobody is blocked on them. They are on your morning page.")
    if good:
        lines.append(f"Some good news: {len(good)} {'thing' if len(good) == 1 else 'things'} went well.")
        good = sorted(good, key=lambda i: "merged" not in (i["why"] or ""))
        for it in good[:2]:
            short = it["repo"].split("/")[-1]
            lines.append(tidy_speech(it["say"], me) if it["say"] else f"In {short}, {it['why']}.")
    if noise:
        verb = "I marked them read" if tidied else "You can ignore them"
        lines.append(f"The other {len(noise)} were noise: {noise_summary(noise)}. {verb}.")
    lines.append(thought if thought.endswith((".", "!", "?")) else thought + ".")
    lines.append("That is all. Go back to sleep for five more minutes. You have earned it.")
    return lines


def speak(lines, out_mp3: Path):
    """Kokoro (open weights, Apache-2.0) on the CPU. Nothing is sent anywhere."""
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(str(config.KOKORO_DIR / "kokoro-v1.0.onnx"), str(config.KOKORO_DIR / "voices-v1.0.bin"))
    chunks, sr = [], 24000
    for line in lines:
        lang = "en-gb" if config.VOICE.startswith("b") else "en-us"
        samples, sr = k.create(line, voice=config.VOICE, speed=config.SPEED, lang=lang)
        chunks += [samples, np.zeros(int(sr * 0.45), dtype=samples.dtype)]
    wav = out_mp3.with_suffix(".wav")
    sf.write(wav, np.concatenate(chunks), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "96k", str(out_mp3)], check=True)
    wav.unlink()
    return round(sum(len(c) for c in chunks) / sr, 1)
