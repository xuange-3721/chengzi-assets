#!/usr/bin/env python3
"""Asset repo voice generator: reads assets/manifest.json, incrementally generates
edge-tts mp3 for every english word / hanzi into assets/voice/ plus index.json."""
import json, asyncio, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MANIFEST = ROOT / "assets" / "manifest.json"
VOICE = ROOT / "assets" / "voice"

def file_for(word, lang):
    if lang == "zh-CN":
        return "zh_" + "_".join(f"{ord(c):04x}" for c in word) + ".mp3"
    slug = re.sub(r"[^a-z0-9]+", "_", word.lower()).strip("_") or "word"
    return "en_" + slug + ".mp3"

async def main():
    import edge_tts
    VOICE.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mapping, jobs = {}, []
    def add(word, lang, voice):
        fn = file_for(word, lang)
        mapping[word] = {"file": fn, "lang": lang}
        p = VOICE / fn
        if not (p.exists() and p.stat().st_size > 1000):
            jobs.append((word, voice, p))
    add("Try again", "en-US", "en-US-JennyNeural")
    mapping["__tryagain__"] = mapping.pop("Try again")
    for w in man.get("words", []):
        wd = str(w.get("word", "")).strip()
        if wd: add(wd, "en-US", "en-US-JennyNeural")
    for h in man.get("hanzi", []):
        hd = str(h.get("word", "")).strip()
        if hd: add(hd, "zh-CN", "zh-CN-XiaoxiaoNeural")
    keep = {v["file"] for v in mapping.values()}
    for f in VOICE.glob("*.mp3"):
        if f.name not in keep: f.unlink()
    print(f"MANIFEST words={len(man.get('words',[]))} hanzi={len(man.get('hanzi',[]))} need={len(jobs)}")
    for i, (text, voice, path) in enumerate(jobs, 1):
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, voice, rate="-5%").save(str(path))
                if path.stat().st_size < 500: raise RuntimeError("too small")
                print(f"[{i}/{len(jobs)}] {path.name} {path.stat().st_size}B")
                break
            except Exception as e:
                if attempt == 3: raise
                await asyncio.sleep(2)
    (VOICE / "index.json").write_text(json.dumps(mapping, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"DONE entries={len(mapping)}")

asyncio.run(main())
