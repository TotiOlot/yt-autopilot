"""Prueba sin APIs: genera audio, imágenes y clips sintéticos y monta un vídeo corto + miniatura."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw  # noqa: E402

from pipeline import editor, thumbnail  # noqa: E402
from pipeline.common import OUT, load_config, probe_duration, run  # noqa: E402

cfg = load_config()
cfg["production"]["resolution"] = [1280, 720]
work = OUT / "demo"; work.mkdir(parents=True, exist_ok=True)

texts = ["In 1846, a dentist walked into a crowded Boston operating theatre with a glass flask.",
         "What happened in the next ten minutes would change surgery forever.",
         "But the man who made it possible would die penniless, and nobody remembers his name."]
files, durs, words, off = [], [], [], 0.0
for i, t in enumerate(texts):
    d = 0.42 * len(t.split()) + 0.35
    f = work / f"a{i}.wav"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency={220 + 60 * i}:duration={d}", "-ar", "44100", "-ac", "2", str(f)])
    d = probe_duration(f)
    step = (d - 0.35) / len(t.split())
    for j, w in enumerate(t.split()):
        words.append({"w": w, "start": off + j * step, "end": off + (j + 1) * step})
    files.append(f); durs.append(d); off += d
audio = {"files": files, "durations": durs, "words": words, "total": off}

plan = []
for i, d in enumerate(durs):
    shots = []
    for k in range(2):
        if k == 0:
            p = work / f"img{i}.jpg"
            img = Image.new("RGB", (1600, 1000), (40 + 50 * i, 30, 60))
            dr = ImageDraw.Draw(img)
            for x in range(0, 1600, 80):
                dr.line([(x, 0), (x + 400, 1000)], fill=(200, 150 + 20 * i, 90), width=6)
            img.save(p); shots.append({"path": p, "kind": "photo", "duration": d / 2})
        else:
            p = work / f"clip{i}.mp4"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)])
            shots.append({"path": p, "kind": "video", "duration": d / 2})
    plan.append(shots)

v = editor.assemble(cfg, plan, audio, work / "edit", OUT / "demo.mp4")
t = thumbnail.make_thumbnail(work / "img0.jpg", "The Forgotten Painkiller", OUT / "demo.jpg")
print("OK", v, probe_duration(v), t)
