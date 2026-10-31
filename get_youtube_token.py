"""Ejecútalo UNA vez en tu ordenador para autorizar la subida a tu canal.

1. Descarga el archivo client_secret.json de Google Cloud (ver GUIA.md, paso 6) y ponlo en esta carpeta.
2. pip install google-auth-oauthlib
3. python get_youtube_token.py
4. Se abre el navegador: elige la cuenta del canal y acepta.
5. Copia los tres valores que aparecen en pantalla a los Secrets de GitHub.
"""
import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
info = json.load(open("client_secret.json"))["installed"]
print("\nCopia estos valores en GitHub > Settings > Secrets and variables > Actions:\n")
print("YT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
