import json
import os
import sys
from ytmusicapi import YTMusic

# Protocolo: C# manda UNA linea JSON por peticion; Python responde UNA linea JSON.
# Todo lo que se imprima "por error" se desvia a stderr para no romper el protocolo.
real_out = sys.stdout
sys.stdout = sys.stderr
real_out.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

def build_client(auth_path):
    with open(auth_path, encoding="utf-8") as f:
        data = json.load(f)
    if "refresh_token" in data:  # archivo creado con "ytmusicapi oauth"
        from ytmusicapi.auth.oauth import OAuthCredentials
        creds = OAuthCredentials(
            client_id=os.environ["YTM_CLIENT_ID"],
            client_secret=os.environ["YTM_CLIENT_SECRET"]
        )
        return YTMusic(auth_path, oauth_credentials=creds)
    return YTMusic(auth_path)  # archivo creado con "ytmusicapi browser"

def to_item(t):
    artists = " ".join(a.get("name", "") for a in (t.get("artists") or []) if a)
    return {
        "videoId": t.get("videoId"),
        "title": t.get("title", ""),
        "artist": artists,
        "duration": t.get("duration_seconds"),
    }

def handle(yt, req):
    cmd = req.get("cmd")
    if cmd == "liked":
        # get_liked_songs devuelve solo 100 por defecto; pedimos hasta 5000.
        data = yt.get_liked_songs(limit=5000)
        items = [to_item(t) for t in data.get("tracks", [])]
    elif cmd == "search":
        results = yt.search(req["query"], filter="songs", limit=5)
        items = [to_item(t) for t in results]
    elif cmd == "like":
        yt.rate_song(req["videoId"], "LIKE")
        return {"ok": True}
    else:
        return {"error": "comando desconocido: " + str(cmd)}

    return {"items": [i for i in items if i["videoId"]]}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "falta la ruta del archivo de autenticacion"}),
              file=real_out, flush=True)
        return 1

    yt = build_client(sys.argv[1])

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            if req.get("cmd") == "quit":
                break
            resp = handle(yt, req)
        except Exception as e:
            resp = {"error": type(e).__name__ + ": " + str(e)}
        print(json.dumps(resp, ensure_ascii=False), file=real_out, flush=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())