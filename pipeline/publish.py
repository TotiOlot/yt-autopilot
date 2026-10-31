"""Paso 7 — Publicación.

mode "review":  email con los vídeos listos (título, descripción, tags y enlace de descarga).
mode "youtube": subida programada a tu canal. Requiere que Google haya auditado tu proyecto de API;
                sin auditoría, YouTube bloquea los vídeos subidos por API en privado.
"""
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from .common import env, log

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def next_slots(cfg: dict, n: int) -> list[datetime]:
    pc = cfg["publish"]
    wanted = [DAYS.index(d.lower()) for d in pc["schedule_days"]]
    t = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    slots = []
    while len(slots) < n:
        t += timedelta(days=1)
        if t.weekday() in wanted:
            slots.append(t.replace(hour=pc["schedule_hour_utc"]))
    return slots


def upload_youtube(cfg: dict, video: Path, thumb: Path, meta: dict, when: datetime) -> str:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(None, refresh_token=env("YT_REFRESH_TOKEN"), client_id=env("YT_CLIENT_ID"),
                        client_secret=env("YT_CLIENT_SECRET"), token_uri="https://oauth2.googleapis.com/token",
                        scopes=["https://www.googleapis.com/auth/youtube.upload",
                                "https://www.googleapis.com/auth/youtube"])
    yt = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:4900],
                    "tags": meta.get("tags", [])[:15], "categoryId": cfg["publish"]["category_id"],
                    "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private", "publishAt": when.isoformat().replace("+00:00", "Z"),
                   "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(cfg["publish"].get("made_with_ai_disclosure", True))},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 << 20, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
    log(f"  subido: https://youtu.be/{vid} (programado {when:%a %d %b %H:%M} UTC)")
    return vid


def send_review_email(cfg: dict, items: list[dict], error: str | None = None) -> None:
    to = env("NOTIFY_EMAIL", required=False)
    user = env("SMTP_USER", required=False); pwd = env("SMTP_PASSWORD", required=False)
    if not (to and user and pwd):
        log("Email no configurado; revisa los vídeos en la pestaña Actions de GitHub.")
        return
    run_url = f"{os.environ.get('GITHUB_SERVER_URL', '')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    lines = []
    if error:
        lines.append(f"⚠️ La ejecución tuvo un problema:\n{error}\n")
    lines.append(f"Descarga los vídeos y miniaturas aquí (sección «Artifacts»):\n{run_url}\n")
    for it in items:
        m = it["meta"]
        lines += [
            "=" * 60,
            f"Nº {it['n']} — publicar: {it['slot']:%A %d %b, %H:%M} UTC",
            f"TÍTULO: {m['title']}",
            f"Archivo: {it['video'].name}  |  Miniatura: {it['thumb'].name}",
            f"YouTube: {it.get('youtube_url', 'pendiente de subir (modo review)')}",
            "", "DESCRIPCIÓN:", m["description"], "",
            "TAGS: " + ", ".join(m.get("tags", [])), "",
        ]
    lines.append("Checklist (5 min por vídeo): ¿datos correctos? ¿imágenes coherentes? ¿título honesto? "
                 "Al subir, marca «Contenido alterado o sintético: Sí».")
    msg = EmailMessage()
    msg["Subject"] = f"[YT Autopilot] {len(items)} vídeos listos para revisar" + (" (con incidencias)" if error else "")
    msg["From"] = user; msg["To"] = to
    msg.set_content("\n".join(lines))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)
    log(f"Email de revisión enviado a {to}")
