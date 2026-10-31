"""Utilidades compartidas: configuración, rutas, logs, llamadas a Claude."""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
OUT = ROOT / "output"


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, required: bool = True) -> str | None:
    val = os.environ.get(name)
    if required and not val:
        sys.exit(f"[ERROR] Falta la variable de entorno {name}. Añádela en GitHub > Settings > Secrets.")
    return val


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {msg}", flush=True)


def run(cmd: list[str]) -> None:
    """Ejecuta un comando (ffmpeg) y muestra el error si falla."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Comando falló: {' '.join(cmd[:6])}...\n{res.stderr[-2000:]}")


def probe_duration(path: Path) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(res.stdout.strip())


def slugify(text: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen] or "video"


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_json(text: str):
    """Extrae el primer bloque JSON de la respuesta del modelo."""
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    raw = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


def ask_claude(cfg: dict, system: str, prompt: str, max_tokens: int = 16000, web_search: bool = False) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=env("ANTHROPIC_API_KEY"))
    kwargs = {}
    if web_search and cfg["models"].get("use_web_search", True):
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}]
    msg = client.messages.create(
        model=cfg["models"]["claude"],
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    # Con búsqueda web hay varios bloques; el texto final es la respuesta.
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
