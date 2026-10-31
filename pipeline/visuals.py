"""Paso 4 — Material visual libre de derechos.

Proveedor principal: Pixabay (PIXABAY_API_KEY). Si existe PEXELS_API_KEY también se usa como extra.
Vídeo cuando hay; si no, foto con efecto Ken Burns.
"""
import os
from pathlib import Path

import requests

from .common import log


def _pixabay_videos(query: str, n: int = 12) -> list[dict]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    r = requests.get("https://pixabay.com/api/videos/", timeout=30,
                     params={"key": key, "q": query[:100], "per_page": max(3, n), "safesearch": "true"})
    if r.status_code != 200:
        return []
    out = []
    for h in r.json().get("hits", []):
        v = h["videos"]
        best = next((v[k] for k in ("large", "medium") if v.get(k, {}).get("url") and v[k]["width"] >= 1280), None)
        if best and best["width"] >= best["height"]:
            out.append({"id": f"xv{h['id']}", "url": best["url"], "kind": "video"})
    return out


def _pixabay_photos(query: str, n: int = 5) -> list[dict]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    r = requests.get("https://pixabay.com/api/", timeout=30,
                     params={"key": key, "q": query[:100], "per_page": max(3, n), "image_type": "photo",
                             "orientation": "horizontal", "min_width": 1600, "safesearch": "true"})
    if r.status_code != 200:
        return []
    return [{"id": f"xp{h['id']}", "url": h["largeImageURL"], "kind": "photo"} for h in r.json().get("hits", [])]


def _pexels_videos(query: str, n: int = 10) -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key}, timeout=30,
                     params={"query": query, "per_page": n, "orientation": "landscape"})
    if r.status_code != 200:
        return []
    out = []
    for v in r.json().get("videos", []):
        files = [f for f in v["video_files"] if f.get("width") and 1280 <= f["width"] <= 2560 and f.get("file_type") == "video/mp4"]
        if files:
            best = min(files, key=lambda f: abs(f["width"] - 1920))
            out.append({"id": f"v{v['id']}", "url": best["link"], "kind": "video"})
    return out


def _pexels_photos(query: str, n: int = 5) -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key}, timeout=30,
                     params={"query": query, "per_page": n, "orientation": "landscape"})
    if r.status_code != 200:
        return []
    return [{"id": f"p{p['id']}", "url": p["src"]["large2x"], "kind": "photo"} for p in r.json().get("photos", [])]


def search_videos(query: str) -> list[dict]:
    return _pixabay_videos(query) + _pexels_videos(query)


def search_photo(query: str, n: int = 5) -> list[dict]:
    return _pixabay_photos(query, n) + _pexels_photos(query, n)


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        with requests.get(url, stream=True, timeout=120, headers={"User-Agent": "yt-autopilot/1.0"}) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
    return dest


def gather(sections: list[dict], durations: list[float], shot_seconds: float, workdir: Path) -> list[list[dict]]:
    """Para cada sección devuelve la lista de planos [{path, kind, duration}] que cubren su duración."""
    if not (os.environ.get("PIXABAY_API_KEY") or os.environ.get("PEXELS_API_KEY")):
        raise SystemExit("[ERROR] Falta PIXABAY_API_KEY en los Secrets de GitHub.")
    workdir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    plan = []
    for i, (sec, dur) in enumerate(zip(sections, durations)):
        needed = max(1, round(dur / shot_seconds))
        queries = sec.get("visual_queries", [])[:3]
        cands = []
        for q in queries:
            cands += [c for c in search_videos(q) if c["id"] not in used]
        if len(cands) < needed:
            for q in queries:
                cands += [c for c in search_photo(q) if c["id"] not in used]
        chosen, seen = [], set()
        for c in cands:
            if c["id"] in seen:
                continue
            seen.add(c["id"]); chosen.append(c)
            if len(chosen) == needed:
                break
        if not chosen:
            raise RuntimeError(f"Sin material visual para la sección {i}: {queries}")
        while len(chosen) < needed:            # reutiliza si faltan planos
            chosen.append(chosen[len(chosen) % len(chosen)])
        shot = dur / needed
        shots = []
        for c in chosen:
            ext = ".mp4" if c["kind"] == "video" else ".jpg"
            p = _download(c["url"], workdir / f"{c['id']}{ext}")
            used.add(c["id"])
            shots.append({"path": p, "kind": c["kind"], "duration": shot})
        plan.append(shots)
        log(f"  visuales sección {i + 1}: {len(shots)} planos")
    return plan
