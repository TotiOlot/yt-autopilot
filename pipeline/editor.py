"""Paso 5 — Montaje automático con ffmpeg: planos + voz + música + subtítulos."""
import random
from pathlib import Path

from .common import ASSETS, log, run


def _ts(t: float) -> str:
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(words: list[dict], path: Path, w: int, h: int, font: str) -> None:
    """Subtítulos por bloques cortos (máx. 7 palabras o hasta un signo de puntuación)."""
    size = int(h * 0.055)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{max(2, size // 14)},1,2,80,80,{int(h * 0.08)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines, chunk = [], []
    for wd in words:
        chunk.append(wd)
        if len(chunk) >= 7 or wd["w"][-1] in ".,;:!?":
            lines.append(chunk); chunk = []
    if chunk:
        lines.append(chunk)
    events = []
    for i, c in enumerate(lines):
        end = c[-1]["end"]
        if i + 1 < len(lines):
            end = min(end + 0.25, lines[i + 1][0]["start"])
        text = " ".join(x["w"] for x in c).replace("{", "(").replace("}", ")")
        events.append(f"Dialogue: 0,{_ts(c[0]['start'])},{_ts(end)},Default,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def _render_shot(shot: dict, out: Path, w: int, h: int, fps: int) -> None:
    d = f"{shot['duration']:.3f}"
    look = "eq=saturation=0.92:contrast=1.04,vignette=PI/5"
    if shot["kind"] == "video":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1,{look}"
        cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(shot["path"]), "-t", d, "-an", "-vf", vf]
    else:
        frames = int(shot["duration"] * fps) + 1
        zin = random.choice(["min(zoom+0.0007,1.15)", "if(eq(on,1),1.15,max(zoom-0.0007,1.0))"])
        vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
              f"zoompan=z='{zin}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},"
              f"setsar=1,{look}")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(shot["path"]), "-t", d, "-vf", vf]
    run(cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])


def assemble(cfg: dict, plan: list[list[dict]], audio: dict, workdir: Path, out_path: Path) -> Path:
    p = cfg["production"]
    w, h = p["resolution"]; fps = p["fps"]
    workdir.mkdir(parents=True, exist_ok=True)

    # 1) planos normalizados
    seg_list = workdir / "segments.txt"
    entries = []
    n = 0
    for shots in plan:
        for shot in shots:
            seg = workdir / f"shot_{n:04d}.mp4"
            _render_shot(shot, seg, w, h, fps)
            entries.append(f"file '{seg.name}'")
            n += 1
    seg_list.write_text("\n".join(entries) + "\n")
    log(f"  {n} planos renderizados")
    video_only = workdir / "video_only.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(seg_list), "-c", "copy", str(video_only)])

    # 2) voz completa
    alist = workdir / "audio.txt"
    alist.write_text("\n".join(f"file '{Path(f).resolve()}'" for f in audio["files"]) + "\n")
    voice = workdir / "voice.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(alist), "-c", "copy", str(voice)])

    # 3) subtítulos
    font_file = next((ASSETS / "fonts").glob("*.ttf"), None)
    font_name = "Anton" if font_file and "anton" in font_file.name.lower() else "DejaVu Sans"
    vf = "null"
    if p.get("burn_subtitles", True):
        ass = workdir / "subs.ass"
        write_ass(audio["words"], ass, w, h, font_name)
        vf = f"subtitles={ass}:fontsdir={ASSETS / 'fonts'}"

    # 4) mezcla final con música opcional
    music = sorted((ASSETS / "music").glob("*.mp3"))
    total = f"{audio['total']:.3f}"
    cmd = ["ffmpeg", "-y", "-i", str(video_only), "-i", str(voice)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(random.choice(music))]
        af = (f"[2:a]volume={p['music_volume']},afade=t=out:st={audio['total'] - 3:.2f}:d=3[m];"
              f"[1:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]")
    else:
        af = "[1:a]loudnorm=I=-14:TP=-1.5[a]"
    cmd += ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[a]", "-t", total,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out_path)]
    run(cmd)
    log(f"  vídeo final: {out_path.name} ({audio['total'] / 60:.1f} min)")
    return out_path
