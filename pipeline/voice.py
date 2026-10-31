"""Paso 3 — Voz con ElevenLabs, con marcas de tiempo por carácter (para subtítulos exactos)."""
import base64
from pathlib import Path

import requests

from .common import env, log, probe_duration, run

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"


def _words_from_alignment(al: dict, offset: float) -> list[dict]:
    words, cur, start = [], "", None
    chars = al["characters"]; starts = al["character_start_times_seconds"]; ends = al["character_end_times_seconds"]
    for ch, s, e in zip(chars, starts, ends):
        if ch.isspace():
            if cur:
                words.append({"w": cur, "start": start + offset, "end": last_end + offset})
                cur, start = "", None
            continue
        if start is None:
            start = s
        cur += ch
        last_end = e
    if cur:
        words.append({"w": cur, "start": start + offset, "end": last_end + offset})
    return words


def synthesize(cfg: dict, sections: list[dict], workdir: Path) -> dict:
    """Genera un mp3 por sección. Devuelve rutas, duraciones y palabras con tiempos globales."""
    key = env("ELEVENLABS_API_KEY")
    voice = cfg["models"]["elevenlabs_voice_id"]
    workdir.mkdir(parents=True, exist_ok=True)
    files, durations, words = [], [], []
    offset = 0.0
    prev_text = ""
    for i, sec in enumerate(sections):
        body = {
            "text": sec["narration"],
            "model_id": cfg["models"]["elevenlabs_model"],
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15},
            "previous_text": prev_text[-500:] or None,   # entonación continua entre secciones
        }
        r = requests.post(API.format(voice=voice), json=body, timeout=300,
                          headers={"xi-api-key": key, "Content-Type": "application/json"},
                          params={"output_format": "mp3_44100_128"})
        r.raise_for_status()
        data = r.json()
        raw = workdir / f"sec_{i:02d}_raw.mp3"
        raw.write_bytes(base64.b64decode(data["audio_base64"]))
        # añade 0,35 s de pausa al final de cada sección
        f = workdir / f"sec_{i:02d}.wav"
        run(["ffmpeg", "-y", "-i", str(raw), "-af", "apad=pad_dur=0.35", "-ar", "44100", "-ac", "2", str(f)])
        d = probe_duration(f)
        words += _words_from_alignment(data["alignment"], offset)
        files.append(f); durations.append(d)
        offset += d
        prev_text += " " + sec["narration"]
        log(f"  voz sección {i + 1}/{len(sections)}: {d:.1f}s")
    return {"files": files, "durations": durations, "words": words, "total": offset}
