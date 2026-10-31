"""Paso 1 — Buscar 'outliers': vídeos del nicho con muchas más visitas que suscriptores tiene su canal.

Usa la YouTube Data API (clave gratuita). Hace lo mismo que el filtro de outliers de NexLev,
pero de forma desatendida. Las URLs que pegues en config.yaml (manual_outlier_urls) van primero.
"""
import re
from datetime import datetime, timedelta, timezone

import requests

from .common import env, log

API = "https://www.googleapis.com/youtube/v3"


def _iso_minutes(d: str) -> float:
    h = re.search(r"(\d+)H", d); m = re.search(r"(\d+)M", d); s = re.search(r"(\d+)S", d)
    return (int(h.group(1)) if h else 0) * 60 + (int(m.group(1)) if m else 0) + (int(s.group(1)) if s else 0) / 60


def _get(endpoint: str, **params) -> dict:
    params["key"] = env("YOUTUBE_API_KEY")
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _video_ids_from_urls(urls: list[str]) -> list[str]:
    ids = []
    for u in urls:
        m = re.search(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})", u)
        if m:
            ids.append(m.group(1))
    return ids


def find_outliers(cfg: dict) -> list[dict]:
    rc = cfg["research"]
    after = (datetime.now(timezone.utc) - timedelta(days=rc["published_within_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")

    ids = _video_ids_from_urls(rc.get("manual_outlier_urls") or [])
    manual = set(ids)
    for q in rc["search_queries"]:
        res = _get("search", part="id", q=q, type="video", order="viewCount", publishedAfter=after,
                   videoDuration="medium" if rc["min_duration_minutes"] < 20 else "long",
                   relevanceLanguage="en", maxResults=25)
        ids += [it["id"]["videoId"] for it in res.get("items", [])]
    ids = list(dict.fromkeys(ids))
    log(f"Investigación: {len(ids)} vídeos candidatos")

    videos = []
    for i in range(0, len(ids), 50):
        res = _get("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        videos += res.get("items", [])

    channel_ids = list({v["snippet"]["channelId"] for v in videos})
    subs = {}
    for i in range(0, len(channel_ids), 50):
        res = _get("channels", part="statistics", id=",".join(channel_ids[i:i + 50]))
        for c in res.get("items", []):
            subs[c["id"]] = int(c["statistics"].get("subscriberCount", 0) or 0)

    out = []
    for v in videos:
        views = int(v["statistics"].get("viewCount", 0))
        minutes = _iso_minutes(v["contentDetails"]["duration"])
        is_manual = v["id"] in manual
        if not is_manual and (views < rc["min_views"] or minutes < rc["min_duration_minutes"]):
            continue
        s = max(subs.get(v["snippet"]["channelId"], 1), 1000)
        out.append({
            "id": v["id"],
            "url": f"https://www.youtube.com/watch?v={v['id']}",
            "title": v["snippet"]["title"],
            "channel": v["snippet"]["channelTitle"],
            "description": v["snippet"].get("description", "")[:1200],
            "views": views,
            "subscribers": subs.get(v["snippet"]["channelId"], 0),
            "minutes": round(minutes, 1),
            "outlier_score": round(views / s, 2),
            "manual": is_manual,
        })
    out.sort(key=lambda x: (x["manual"], x["outlier_score"]), reverse=True)
    top = out[: rc["top_outliers"]]
    for o in top:
        log(f"  outlier x{o['outlier_score']}: {o['title']} ({o['views']:,} visitas)")
    return top
