"""
DJ Deck – fronta přání (song requests board)
Jeden soubor: FastAPI backend + stránka pro hosty.

Nasazení na Render.com:
  - Build command:  pip install -r requirements.txt
  - Start command:  uvicorn main:app --host 0.0.0.0 --port $PORT
  - Environment variable:  ADMIN_TOKEN = <tvoje tajné heslo>   (stejné pak vložíš do DJ decku)

Fronta se drží v paměti – pro jednu párty ideální. Když se server restartuje, přání se vynulují.
"""
import os
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "zmen-me")
MAX_REQUESTS = 400
MAX_TITLE = 200
MAX_NOTE = 300

app = FastAPI(title="DJ Deck – přání")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory fronta přání
REQUESTS = []


class ReqIn(BaseModel):
    title: str
    artist: str = ""
    note: str = ""


def clean(s, n):
    return (s or "").strip()[:n]


@app.get("/api/requests")
def list_requests():
    return {"requests": REQUESTS}


@app.post("/api/requests")
def add_request(r: ReqIn):
    title = clean(r.title, MAX_TITLE)
    if not title:
        raise HTTPException(status_code=400, detail="Chybí název skladby.")
    if len(REQUESTS) >= MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Fronta přání je plná.")
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "artist": clean(r.artist, MAX_TITLE),
        "note": clean(r.note, MAX_NOTE),
        "ts": int(time.time()),
    }
    REQUESTS.append(item)
    return item


@app.delete("/api/requests/{rid}")
def delete_request(rid: str, token: str = ""):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Špatný admin token.")
    global REQUESTS
    before = len(REQUESTS)
    REQUESTS = [x for x in REQUESTS if x["id"] != rid]
    return {"ok": True, "removed": before - len(REQUESTS)}


@app.delete("/api/requests")
def clear_requests(token: str = ""):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Špatný admin token.")
    REQUESTS.clear()
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def guest_page():
    return GUEST_HTML


GUEST_HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Přání do fronty – DJ</title>
<style>
  :root{--bg:#0d0e12;--panel:#16181f;--raised:#1c1f28;--line:#282c37;--steel:#8891a5;--text:#e8eaf0;--muted:#6b7280;--accent:#22c55e}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:radial-gradient(900px 500px at 50% -10%,#1a1d27,transparent 60%),var(--bg);color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;min-height:100vh;padding:18px;line-height:1.4}
  .wrap{max-width:560px;margin:0 auto}
  h1{font-size:26px;letter-spacing:.5px;margin-bottom:2px}
  .sub{color:var(--muted);font-size:14px;margin-bottom:18px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
  label{display:block;font-size:13px;color:var(--muted);margin:10px 0 4px;text-transform:uppercase;letter-spacing:1px}
  input,textarea{width:100%;background:#0b0c10;border:1px solid var(--line);color:var(--text);padding:12px;border-radius:8px;font-size:16px;font-family:inherit}
  input:focus,textarea:focus{outline:none;border-color:var(--steel)}
  textarea{resize:vertical;min-height:60px}
  button{width:100%;margin-top:14px;background:var(--accent);color:#04120a;border:0;padding:13px;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer}
  button:active{transform:translateY(1px)}
  button:disabled{opacity:.6;cursor:not-allowed}
  .msg{min-height:20px;font-size:14px;margin-top:10px;text-align:center}
  .msg.ok{color:var(--accent)} .msg.err{color:#fca5a5}
  h2{font-size:15px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin:6px 0 10px}
  .item{background:var(--raised);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:8px}
  .item .t{font-size:16px;font-weight:600}
  .item .a{font-size:14px;color:var(--steel)}
  .item .n{font-size:13px;color:var(--muted);margin-top:3px;font-style:italic}
  .empty{color:var(--muted);text-align:center;padding:16px;font-size:14px}
</style>
</head>
<body>
  <div class="wrap">
    <h1>🎧 Poslat přání DJ</h1>
    <div class="sub">Napiš, co si chceš pustit. DJ to uvidí u sebe.</div>

    <div class="card">
      <label>Název skladby *</label>
      <input id="title" maxlength="200" placeholder="Např. Blinding Lights">
      <label>Interpret</label>
      <input id="artist" maxlength="200" placeholder="Např. The Weeknd">
      <label>Poznámka (nepovinné)</label>
      <textarea id="note" maxlength="300" placeholder="Např. k narozeninám pro Terku :)"></textarea>
      <button id="send">Poslat přání</button>
      <div class="msg" id="msg"></div>
    </div>

    <h2>Aktuální přání</h2>
    <div id="list"><div class="empty">Zatím žádná přání – buď první!</div></div>
  </div>

<script>
  function esc(s){return (s||"").replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function setMsg(t,cls){var m=document.getElementById('msg');m.textContent=t||"";m.className="msg"+(cls?(" "+cls):"");}

  document.getElementById('send').addEventListener('click',function(){
    var title=document.getElementById('title').value.trim();
    if(!title){setMsg("Napiš aspoň název skladby.","err");return;}
    var btn=document.getElementById('send');btn.disabled=true;setMsg("Posílám…");
    fetch('/api/requests',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:title,artist:document.getElementById('artist').value,note:document.getElementById('note').value})})
      .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j};});})
      .then(function(res){
        btn.disabled=false;
        if(!res.ok){setMsg(res.j.detail||"Nepovedlo se odeslat.","err");return;}
        setMsg("Hotovo! Přání odesláno 🎉","ok");
        document.getElementById('title').value="";document.getElementById('artist').value="";document.getElementById('note').value="";
        load();
      })
      .catch(function(){btn.disabled=false;setMsg("Chyba spojení, zkus to znovu.","err");});
  });

  function load(){
    fetch('/api/requests').then(function(r){return r.json();}).then(function(d){
      var list=document.getElementById('list');var reqs=(d.requests||[]);
      if(reqs.length===0){list.innerHTML='<div class="empty">Zatím žádná přání – buď první!</div>';return;}
      var html="";
      reqs.slice().reverse().forEach(function(x){
        html+='<div class="item"><div class="t">'+esc(x.title)+'</div>'+
          (x.artist?'<div class="a">'+esc(x.artist)+'</div>':'')+
          (x.note?'<div class="n">"'+esc(x.note)+'"</div>':'')+'</div>';
      });
      list.innerHTML=html;
    }).catch(function(){});
  }
  load();setInterval(load,5000);
</script>
</body>
</html>"""
