#!/usr/bin/env python3
"""Rapport sécurité quotidien 


Usage:
    report.py                # silencieux, écrit dans report.log
    report.py --dry-run      # affiche seulement et 
    report.py --notify       # envoie l alrt  aussi sur Telegram
    report.py --quiet        # aucune sortie fichier ni console
"""
import argparse, json, os, shutil, socket, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

LOG = Path(__file__).with_name("report.log")

def load_config(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def check_cameras(cameras, timeout=3):
    out = []
    for c in cameras:
        try:
            with socket.create_connection((c["host"], int(c.get("port", 554))), timeout=timeout):
                out.append((c["name"], True))
        except OSError:
            out.append((c["name"], False))
    return out

def check_disks(disks, warn):
    out = []
    for d in disks:
        try:
            u = shutil.disk_usage(d["path"])
            pct = u.used / u.total * 100
            out.append({"name": d.get("name", d["path"]), "free_gb": u.free/1e9,
                        "total_gb": u.total/1e9, "percent": pct, "warn": pct >= warn, "error": None})
        except OSError as e:
            out.append({"name": d.get("name", d["path"]), "error": str(e), "warn": True})
    return out

def night_window(s, e, now=None):
    now = now or datetime.now()
    sh, sm = map(int, s.split(":")); eh, em = map(int, e.split(":"))
    end = now.replace(hour=eh, minute=em, second=0, microsecond=0)
    if end > now: end -= timedelta(days=1)
    start = end.replace(hour=sh, minute=sm)
    if start >= end: start -= timedelta(days=1)
    return start, end

def count_events(cfg, start , end):
    root = Path(cfg["recordings_path"])
    exts = {x.lower() for x in cfg.get("extensions", [".mp4", ".mkv", ".jpg"])}
    if not root.exists(): return None
    t0, t1 = start.timestamp(), end.timestamp()
    per, total = {}, 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            try:
                if t0 <= p.stat().st_mtime <= t1:
                    parts = p.relative_to(root).parts
                    cam = parts[0] if len(parts) > 1 else "(root)"
                    per[cam] = per.get(cam, 0) + 1; total += 1
            except OSError: pass
    return total, per

def build(cfg):
    now = datetime.now()
    L = [f"[{now:%Y-%m-%d %H:%M}] report"]; problems = 0
    cams = check_cameras(cfg.get("cameras", []), cfg.get("timeout", 3))
    online = sum(1 for _, ok in cams if ok)
    L.append(f"cameras: {online}/{len(cams)} online")
    for n, ok in cams:
        if not ok: L.append(f"  DOWN: {n}"); problems += 1
    L.append("disks:")
    for d in check_disks(cfg.get("disks", []), cfg.get("disk_warn_percent", 85)):
        if d["error"]:
            L.append(f"  {d['name']}: error ({d['error']})"); problems += 1
        else:
            tag = "WARN" if d["warn"] else "OK"
            problems += d["warn"]
            L.append(f"  {d['name']}: {d['percent']:.0f}% used, {d['free_gb']:.0f}GB free [{tag}]")
    ev = cfg.get("events")
    if ev:
        s, e = night_window(ev.get("night_start", "22:00"), ev.get("night_end", "07:00"))
        L.append(f"night {s:%H:%M}-{e:%H:%M}:")
        r = count_events(ev, s, e)
        if r is None:
            L.append("  recordings folder missing"); problems += 1
        else:
            tot, per = r
            L.append(f"  {tot} event(s)")
            for c, n in sorted(per.items(), key=lambda x: -x[1]):
                L.append(f"  - {c}: {n}")
    L.append("status: OK" if problems == 0 else f"status: {problems} issue(s)")
    return "\n".join(L), problems

def telegram(token, chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        if r.status != 200: raise RuntimeError(f"telegram http {r.status}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default=str(Path(__file__).with_name("config.json")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--notify", action="store_true", help="envoyer sur Telegram")
    ap.add_argument("--quiet", action="store_true", help="aucune sortie")
    a = ap.parse_args()
    if not os.path.exists(a.config):
        sys.stderr.write(f"config missing: {a.config}\n"); sys.exit(2)
    cfg = load_config(a.config)
    text, problems = build(cfg)
    if a.dry_run:
        print(text); return
    if not a.quiet:
        try:
            with open(LOG, "a", encoding="utf-8") as f: f.write(text + "\n")
        except OSError: pass
    if a.notify:
        tg = cfg.get("telegram", {})
        tok = os.environ.get("TELEGRAM_TOKEN") or tg.get("bot_token")
        cid = os.environ.get("TELEGRAM_CHAT_ID") or tg.get("chat_id")
        if not tok or not cid:
            sys.stderr.write("telegram creds missing\n"); sys.exit(3)
        try: telegram(tok, cid, text)
        except Exception as e: sys.stderr.write(f"telegram failed: {e}\n"); sys.exit(4)
    sys.exit(0 if problems == 0 else 1)

if __name__ == "__main__":
    main()
