# YT Autopilot — Guía de puesta en marcha

Sistema que **cada domingo, sin que hagas nada**:

1. Busca en YouTube los *outliers* de tu nicho: vídeos con muchas más visitas que suscriptores tiene su canal (lo mismo que el filtro de NexLev).
2. Claude analiza **por qué** funcionan (título, gancho, estructura, giros) y propone temas nuevos.
3. Escribe **3 guiones originales** de unos 10 minutos, investigados con búsqueda web y con fuentes.
4. ElevenLabs genera la voz.
5. Monta cada vídeo: planos de stock de Pexels que cambian cada 6 s, efecto Ken Burns, subtítulos sincronizados, música y volumen normalizado para YouTube.
6. Crea la miniatura, el título, la descripción y los tags.
7. Te manda un **email** con todo listo (modo `review`) o lo **programa en tu canal** martes, jueves y sábado (modo `youtube`).

Tu parte son unos 20 minutos a la semana: revisar el email y darle a publicar.

---

## Costes mensuales

| Concepto | Situación actual | Con el sistema (12 vídeos/mes) | Notas |
|---|---|---|---|
| Claude API (guiones + investigación) | 0 € | ≈ 5–10 $ | Pago por uso |
| ElevenLabs (voz) | 0 € | 22 $ (plan Creator) | ~100.000 caracteres/mes ≈ 12 vídeos de 10 min. Licencia comercial incluida |
| Pexels (imágenes y vídeos) | 0 € | 0 € | Gratis, uso comercial permitido |
| YouTube Data API | 0 € | 0 € | Gratis (cuota diaria de sobra) |
| GitHub Actions (servidor) | 0 € | 0 € | Gratis si el repositorio es **público** (ver nota) |
| NexLev | — | Opcional | Solo para validar el nicho a mano; el sistema no lo necesita |
| **Total** | **0 €** | **≈ 27–32 $/mes** | |

> **Nota sobre GitHub:** en repositorios públicos los minutos de Actions y el almacenamiento de vídeos son gratis. En uno privado tienes 2.000 min/mes y 500 MB de almacenamiento, que se quedan cortos para 3 vídeos de 10 minutos. El código no contiene ninguna clave (van en *Secrets*), así que hacerlo público no expone nada.

---

## Puesta en marcha (unas 2 horas, una sola vez)

### 1. Crear el repositorio
1. Crea una cuenta en github.com si no tienes.
2. **New repository** → nombre `yt-autopilot` → Public → Create.
3. **Add file → Upload files** → arrastra todo el contenido de esta carpeta (incluida `.github`) → Commit.

### 2. Claves que necesitas
Ve a tu repositorio → **Settings → Secrets and variables → Actions → New repository secret** y crea estas:

| Secret | Dónde se consigue |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys (añade 10–20 $ de saldo) |
| `ELEVENLABS_API_KEY` | elevenlabs.io → contrata Creator → Profile → API Keys |
| `PEXELS_API_KEY` | pexels.com/api → gratis, al instante |
| `YOUTUBE_API_KEY` | console.cloud.google.com → nuevo proyecto → activa **YouTube Data API v3** → Credenciales → Crear clave de API |
| `NOTIFY_EMAIL` | El email donde quieres recibir el resumen |
| `SMTP_USER` | Una cuenta de Gmail que envíe el aviso |
| `SMTP_PASSWORD` | Contraseña de aplicación de esa cuenta Gmail (myaccount.google.com → Seguridad → Contraseñas de aplicaciones) |

### 3. Elegir la voz
En ElevenLabs → Voice Library, busca un narrador documental en inglés (filtra por *Narrative & Story*). Copia su **Voice ID** y pégalo en `config.yaml` → `elevenlabs_voice_id`.

### 4. Música (opcional, recomendado)
Descarga 3–5 pistas ambientales de la **Biblioteca de audio de YouTube** (YouTube Studio → Biblioteca de audio, filtra por "Sin atribución") y súbelas a `assets/music/`.

### 5. Primera prueba
Repositorio → pestaña **Actions** → *YT Autopilot semanal* → **Run workflow** → pon `1` en número de vídeos → Run.
Tarda unos 20–30 minutos. Al terminar, el vídeo aparece en **Artifacts** y te llega el email.

**Revisa ese primer vídeo con calma.** Si quieres cambiar el tono, el ritmo o el estilo, edita `config.yaml` (o pídemelo).

### 6. Subida automática a tu canal (cuando quieras)
YouTube bloquea en privado los vídeos subidos por API desde proyectos no auditados. Para activarlo:
1. En el mismo proyecto de Google Cloud: **Pantalla de consentimiento OAuth** → Externo → añade tu email como usuario de prueba.
2. **Credenciales → Crear ID de cliente OAuth → App de escritorio** → descarga el JSON como `client_secret.json`.
3. En tu ordenador: `pip install google-auth-oauthlib` y `python get_youtube_token.py`, y copia los 3 valores a Secrets (`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`).
4. Solicita la auditoría: formulario *YouTube API Services – Audit and Quota Extension*. Uso: "uploading videos to my own channel".
5. Cuando te la aprueben, cambia `publish.mode` a `"youtube"` en `config.yaml`. Desde ese momento los vídeos se programan solos.

Mientras tanto, en modo `review`: descargas los 3 vídeos del email, los subes en YouTube Studio y copias título y descripción (unos 5 minutos por vídeo).

---

## Reglas para no perder la monetización

- **Revisa cada vídeo antes de publicarlo.** Es lo que diferencia un canal con criterio de una "granja de IA", que es lo que YouTube castiga a nivel de canal entero.
- Al subir, marca siempre **"Contenido alterado o sintético: Sí"**. No penaliza el alcance ni la monetización.
- No subas más de los 3 vídeos semanales. Más volumen = más riesgo de que te consideren contenido "producido en masa".
- Si un vídeo tiene un dato dudoso, no lo publiques: mejor 2 buenos que 3 regulares.
- Requisito para monetizar: 1.000 suscriptores + 4.000 horas de visualización en 12 meses. Cuenta con que esto lleva meses.

---

## Ajustes rápidos en `config.yaml`

| Quiero… | Cambia |
|---|---|
| Otro nicho | `channel.niche` y `research.search_queries` |
| Usar outliers de NexLev | Pega URLs en `research.manual_outlier_urls` |
| Vídeos más largos o cortos | `production.target_minutes` |
| Más o menos vídeos | `production.videos_per_run` |
| Otros días de publicación | `publish.schedule_days` |
| Gastar la mitad en voz | `elevenlabs_model: "eleven_turbo_v2_5"` (algo menos natural) |

## Estructura

```
config.yaml              ← todo lo configurable
pipeline/research.py     ← busca outliers (YouTube API)
pipeline/scriptwriter.py ← fórmula + guiones (Claude + búsqueda web)
pipeline/voice.py        ← voz + tiempos por palabra (ElevenLabs)
pipeline/visuals.py      ← vídeos e imágenes (Pexels)
pipeline/editor.py       ← montaje (ffmpeg)
pipeline/thumbnail.py    ← miniatura
pipeline/publish.py      ← email de revisión / subida programada
pipeline/run.py          ← orquestador
.github/workflows/weekly.yml ← ejecución automática cada domingo
data/history.json        ← temas ya hechos (para no repetir)
```
