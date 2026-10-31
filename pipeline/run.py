"""Orquestador: investigación → fórmula → 3 guiones → voz → visuales → montaje → miniatura → publicación.

Uso:  python -m pipeline.run            (ejecución completa)
      python -m pipeline.run --videos 1 (prueba con un solo vídeo)
"""
import argparse
import traceback
from datetime import datetime, timezone

from . import editor, publish, research, scriptwriter, thumbnail, visuals, voice
from .common import DATA, OUT, load_config, load_json, log, save_json, slugify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=int, default=None)
    args = ap.parse_args()

    cfg = load_config()
    n = args.videos or cfg["production"]["videos_per_run"]
    history_path = DATA / "history.json"
    history = load_json(history_path, [])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    OUT.mkdir(exist_ok=True)

    log("1/7 Buscando outliers en YouTube…")
    outliers = research.find_outliers(cfg)
    save_json(OUT / f"{stamp}_outliers.json", outliers)

    log("2/7 Analizando la fórmula ganadora…")
    formula = scriptwriter.analyze_formula(cfg, outliers)
    save_json(OUT / f"{stamp}_formula.json", formula)
    topics = scriptwriter.pick_topics(formula, history, n)

    slots = publish.next_slots(cfg, len(topics))
    done, errors = [], []
    for i, (topic, slot) in enumerate(zip(topics, slots), 1):
        try:
            log(f"=== Vídeo {i}/{len(topics)}: {topic}")
            log("3/7 Escribiendo guion…")
            meta = scriptwriter.write_script(cfg, formula, topic, [h["title"] for h in history])
            slug = f"{stamp}_{i}_{slugify(meta['title'])}"
            work = OUT / "work" / slug
            save_json(OUT / f"{slug}.json", meta)

            log("4/7 Generando voz…")
            audio = voice.synthesize(cfg, meta["sections"], work / "audio")

            log("5/7 Buscando imágenes y vídeos…")
            plan = visuals.gather(meta["sections"], audio["durations"], cfg["production"]["seconds_per_shot"], work / "media")

            log("6/7 Montando vídeo y miniatura…")
            video_path = editor.assemble(cfg, plan, audio, work / "edit", OUT / f"{slug}.mp4")
            bg = visuals.search_photo(meta.get("thumbnail_query") or meta["sections"][0]["visual_queries"][0], 1)
            bg_path = visuals._download(bg[0]["url"], work / "thumb_bg.jpg") if bg else plan[0][0]["path"]
            thumb_path = thumbnail.make_thumbnail(bg_path, meta["thumbnail_text"], OUT / f"{slug}.jpg")

            item = {"n": i, "meta": meta, "video": video_path, "thumb": thumb_path, "slot": slot}
            if cfg["publish"]["mode"] == "youtube":
                log("7/7 Subiendo a YouTube…")
                vid = publish.upload_youtube(cfg, video_path, thumb_path, meta, slot)
                item["youtube_url"] = f"https://youtu.be/{vid}"
            done.append(item)
            history.append({"date": stamp, "topic": topic, "title": meta["title"], "slug": slug,
                            "youtube": item.get("youtube_url")})
            save_json(history_path, history)
        except Exception as e:  # un vídeo fallido no para los demás
            errors.append(f"Vídeo {i} ({topic}): {e}")
            traceback.print_exc()

    publish.send_review_email(cfg, done, "\n".join(errors) or None)
    log(f"Terminado: {len(done)} vídeos OK, {len(errors)} con error.")
    if not done:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
