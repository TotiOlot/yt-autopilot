"""Paso 4 — Material visual libre de derechos desde Pexels (vídeo; si no hay, foto con efecto Ken Burns)."""
from pathlib import Path

import requests

from .common import env, log

PEXELS = "https://api.pexels.com"


def _headers():
    return {"Authorization": env("PEXELS_API_KEY")}


def _search_videos(query: str, n: int = 10) -> list[dict]:
    r = requests.get(f"{PEXELS}/videos/search", headers=_headers(), timeout=30,
                     params={"query": query, "per_page": n, "orientation": "landscape", "size": "medium"})
    if r.status_code != 200:
        return []
    out = []
    for v in r.json().get("videos", []):
        files = [f for f in v["video_files"] if f.get("width") and 1280 <= f["width"] <= 2560 and f.get("file_type") == "video/mp4"]
        if files:
            best = min(files, key=lambda f: abs(f["width"] - 1920))
            out.append({"id": f"v{v['id']}", "url": best["link"], "duration": v["duration"], "kind": "video"})
    return out


def search_photo(query: str, n: int = 5) -> list[dict]:
    r = requests.get(f"{PEXELS}/v1/search", headers=_headers(), timeout=30,
                     params={"query": query, "per_page": n, "orientation": "landscape"})
    if r.status_code != 200:
        return []
    return [{"id": f"p{p['id']}", "url": p["src"]["large2x"], "kind": "photo"} for p in r.json().get("photos", [])]


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
    return dest


def gather(sections: list[dict], durations: list[float], shot_seconds: float, workdir: Path) -> list[list[dict]]:
    """Para cada sección devuelve la lista de planos [{path, kind, duration}] que cubren su duración."""
    workdir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    plan = []
    for i, (sec, dur) in enumerate(zip(sections, durations)):
        needed = max(1, round(dur / shot_seconds))
        cands = []
        for q in sec.get("visual_queries", [])[:3]:
            cands += [c for c in _search_videos(q) if c["id"] not in used]
        if len(cands) < needed:
            for q in sec.get("visual_queries", [])[:3]:
                cands += [c for c in search_photo(q) if c["id"] not in used]
        # alterna entre consultas para dar variedad
        chosen, seen = [], set()
        for c in cands:
            if c["id"] in seen:
                continue
            seen.add(c["id"]); chosen.append(c)
            if len(chosen) == needed:
                break
        if not chosen:
            raise RuntimeError(f"Sin material visual para la sección {i}: {sec.get('visual_queries')}")
        while len(chosen) < needed:            # reutiliza si faltan planos
            chosen.append(chosen[len(chosen) % len(chosen)])
        shot = dur / needed
        shots = []
        for j, c in enumerate(chosen):
            ext = ".mp4" if c["kind"] == "video" else ".jpg"
            p = _download(c["url"], workdir / f"{c['id']}{ext}")
            used.add(c["id"])
            shots.append({"path": p, "kind": c["kind"], "duration": shot})
        plan.append(shots)
        log(f"  visuales sección {i + 1}: {len(shots)} planos")
    return plan
