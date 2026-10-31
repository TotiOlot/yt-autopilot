"""Paso 2 — Claude analiza POR QUÉ funcionan los outliers y escribe guiones nuevos.

Clave para no ser desmonetizado ("inauthentic content"): se copia la ESTRUCTURA
(gancho, ritmo, giros, promesa del título), nunca el tema ni las frases.
Cada guion es un tema distinto, investigado con búsqueda web y con datos verificables.
"""
import json

from .common import ask_claude, extract_json, log

SYSTEM = """You are the head writer of a premium faceless YouTube documentary channel.
You write original, well-researched scripts. You NEVER copy or paraphrase other creators' scripts;
you learn structural patterns (hooks, pacing, open loops, payoff) and apply them to new, different topics.
Accuracy matters: only state facts you can support, prefer primary sources, never invent quotes or numbers.
Never give medical, financial or legal advice; this is history and storytelling."""


def analyze_formula(cfg: dict, outliers: list[dict]) -> dict:
    prompt = f"""Channel niche: {cfg['channel']['niche']}
These are the top outlier videos in the niche (views far above channel size):

{json.dumps(outliers, indent=2, ensure_ascii=False)}

Analyze WHY they over-perform. Return ONLY a JSON object:
{{
  "title_patterns": ["pattern with placeholder, e.g. 'The [Adjective] Story of [Person] Who [Unexpected Act]'"],
  "thumbnail_patterns": ["short description"],
  "hook_formula": "how the first 30 seconds work",
  "structure": ["beat 1", "beat 2", "..."],
  "retention_devices": ["open loops, cliffhangers, reveals..."],
  "topics_already_covered": ["topics of these videos, to AVOID duplicating"],
  "fresh_topic_ideas": ["15 new, specific, true topics in the niche that fit the same psychology but are NOT covered above"]
}}"""
    formula = extract_json(ask_claude(cfg, SYSTEM, prompt, max_tokens=6000))
    log(f"Fórmula analizada: {len(formula.get('fresh_topic_ideas', []))} temas nuevos propuestos")
    return formula


def write_script(cfg: dict, formula: dict, topic: str, done_titles: list[str]) -> dict:
    words = int(cfg["production"]["target_minutes"] * 150)
    prompt = f"""Channel niche: {cfg['channel']['niche']}
Audience: {cfg['channel']['audience']}
Narrator persona: {cfg['channel']['voice_persona']}
Language: {cfg['channel']['language']}

Winning formula extracted from outliers (apply the STRUCTURE only):
{json.dumps(formula, indent=2, ensure_ascii=False)}

Topic for this video: {topic}
Titles already published on our channel (do not repeat): {done_titles[-40:]}

First research the topic with web search to get accurate facts, names, dates and sources.
Then write a complete narration script of about {words} words ({cfg['production']['target_minutes']} minutes spoken).
Rules:
- Spoken style, short sentences, no headings or stage directions inside narration.
- Hook in the first 2 sentences; open a loop that pays off near the end.
- No "smash that like button" filler. One natural subscribe mention near the end is fine.
- 10-16 sections. For each section give 2-3 stock-footage search queries (concrete, visual, 2-4 words,
  e.g. "old surgical tools", "victorian london street", "microscope lab") that a stock library will have.

Return ONLY a JSON object:
{{
  "title": "max 70 chars, curiosity-driven, honest (no clickbait lies)",
  "description": "150-250 words, first 2 lines are a hook, then summary, then 'Sources:' list of URLs",
  "tags": ["10-15 tags"],
  "thumbnail_text": "2-4 WORDS, ALL CAPS",
  "thumbnail_query": "stock photo search query for the thumbnail background",
  "sections": [{{"narration": "...", "visual_queries": ["...", "..."]}}]
}}"""
    script = extract_json(ask_claude(cfg, SYSTEM, prompt, max_tokens=16000, web_search=True))
    n_words = sum(len(s["narration"].split()) for s in script["sections"])
    log(f"Guion: «{script['title']}» — {len(script['sections'])} secciones, {n_words} palabras")
    return script


def pick_topics(formula: dict, history: list[dict], n: int) -> list[str]:
    done = {h["topic"].lower() for h in history}
    ideas = [t for t in formula.get("fresh_topic_ideas", []) if t.lower() not in done]
    return ideas[:n]
