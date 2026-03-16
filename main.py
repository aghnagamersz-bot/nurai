"""
NurAI Whisper API — Hugging Face Spaces Edition
================================================
FastAPI backend untuk analisis tajwid Al-Qur'an.

Perbedaan dari versi Render:
  - Port 7860 (bukan 8000) — WAJIB di HF Spaces
  - Tidak ada self-ping (HF Spaces tidak sleep seperti Render)
  - Cache diarahkan ke /tmp
  - Non-root user compatible
"""

import os, re, json, asyncio, logging, tempfile
from difflib import SequenceMatcher
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nurai")

# ── App ───────────────────────────────────────────────
app = FastAPI(
    title="NurAI Tajwid API",
    description="Analisis bacaan Al-Qur'an via OpenAI Whisper · نُورَى",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — izinkan semua origin (frontend NurAI) ─────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Ganti dengan domain spesifik saat production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────
OPENAI_KEY   = os.getenv("OPENAI_API_KEY", "")
MAX_SIZE_MB  = 10
WHISPER_MODEL = "whisper-1"        # $0.006/mnt
# WHISPER_MODEL = "gpt-4o-mini-transcribe"  # $0.003/mnt — lebih murah & akurat


# ═══════════════════════════════════════════════════
# DATABASE AYAT + HUKUM TAJWID
# ═══════════════════════════════════════════════════
QURAN = {
    "1_1": {
        "arabic": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "latin":  "bismillahirrahmanirrahim",
        "id":     "Dengan nama Allah Yang Maha Pengasih, Maha Penyayang.",
        "rules": [
            {"kata": "اللَّهِ",    "hukum": "mad_thabii",  "tip": "Panjangkan lam 2 harakat"},
            {"kata": "الرَّحْمَٰنِ","hukum": "ghunnah",    "tip": "Dengung nun 2 harakat dari hidung"},
            {"kata": "الرَّحِيمِ", "hukum": "mad_thabii",  "tip": "Panjangkan ya 2 harakat"},
        ],
    },
    "1_2": {
        "arabic": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "latin":  "alhamdu lillahi rabbil alamin",
        "id":     "Segala puji bagi Allah, Tuhan seluruh alam,",
        "rules": [
            {"kata": "لِلَّهِ",    "hukum": "tafkhim",     "tip": "Lam jalalah tebal — sebelumnya kasrah, jadi tipis"},
            {"kata": "الْعَالَمِينَ","hukum": "ghunnah",   "tip": "Nun tasydid — dengung 2 harakat"},
        ],
    },
    "1_3": {
        "arabic": "الرَّحْمَٰنِ الرَّحِيمِ",
        "latin":  "arrahmanirrahim",
        "id":     "Yang Maha Pengasih, Maha Penyayang,",
        "rules": [
            {"kata": "الرَّحْمَٰنِ","hukum": "ghunnah",    "tip": "Dengung 2 harakat"},
            {"kata": "الرَّحِيمِ", "hukum": "mad_thabii",  "tip": "Mad ya 2 harakat"},
        ],
    },
    "1_4": {
        "arabic": "مَالِكِ يَوْمِ الدِّينِ",
        "latin":  "maliki yaumiddin",
        "id":     "Pemilik hari pembalasan.",
        "rules": [
            {"kata": "الدِّينِ",   "hukum": "mad_thabii",  "tip": "Mad ya 2 harakat"},
        ],
    },
    "1_5": {
        "arabic": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ",
        "latin":  "iyyaka nabudu wa iyyaka nastain",
        "id":     "Hanya kepada Engkaulah kami menyembah dan mohon pertolongan.",
        "rules": [
            {"kata": "نَعْبُدُ",   "hukum": "ikhfa",       "tip": "Nun bertemu ain — ikhfa samar 2 harakat"},
            {"kata": "نَسْتَعِينُ","hukum": "ikhfa",       "tip": "Nun bertemu sin — ikhfa samar"},
        ],
    },
    "1_6": {
        "arabic": "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",
        "latin":  "ihdinassiratal mustaqim",
        "id":     "Tunjukkanlah kami jalan yang lurus,",
        "rules": [
            {"kata": "الصِّرَاطَ", "hukum": "tafkhim",     "tip": "Huruf ص — isti'la, baca tebal"},
            {"kata": "الْمُسْتَقِيمَ","hukum": "mad_thabii","tip": "Mad ya 2 harakat di akhir"},
        ],
    },
    "1_7": {
        "arabic": "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ",
        "latin":  "shiratal ladzina anamta alaihim ghairil maghdubi alaihim walad dhallin",
        "id":     "(yaitu) jalan yang Engkau beri nikmat, bukan yang dimurkai dan bukan yang sesat.",
        "rules": [
            {"kata": "الَّذِينَ",  "hukum": "idgham",      "tip": "Idgham bighunnah — lebur dengan dengung"},
            {"kata": "الْمَغْضُوبِ","hukum": "iqlab",      "tip": "Iqlab — nun tanwin → mim samar + dengung"},
            {"kata": "الضَّالِّينَ","hukum": "mad_lazim",  "tip": "Mad lazim — WAJIB 6 harakat, bertemu tasydid"},
        ],
    },
    "112_1": {
        "arabic": "قُلْ هُوَ اللَّهُ أَحَدٌ",
        "latin":  "qul huwal lahu ahad",
        "id":     "Katakanlah: Dialah Allah, Yang Maha Esa.",
        "rules": [
            {"kata": "اللَّهُ",    "hukum": "tafkhim",     "tip": "Lam jalalah tebal — sebelumnya dhammah"},
            {"kata": "أَحَدٌ",    "hukum": "ghunnah",     "tip": "Tanwin — dengung 2 harakat saat waqaf"},
        ],
    },
    "112_2": {
        "arabic": "اللَّهُ الصَّمَدُ",
        "latin":  "allahus shamad",
        "id":     "Allah adalah Tuhan tempat bergantung segala sesuatu.",
        "rules": [
            {"kata": "الصَّمَدُ", "hukum": "qalqalah",    "tip": "Dal di akhir — qalqalah kubra, pantulan kuat"},
        ],
    },
    "112_3": {
        "arabic": "لَمْ يَلِدْ وَلَمْ يُولَدْ",
        "latin":  "lam yalid walam yulad",
        "id":     "Dia tidak beranak dan tidak pula diperanakkan,",
        "rules": [
            {"kata": "يُولَدْ",   "hukum": "qalqalah",    "tip": "Dal di akhir — qalqalah kubra saat waqaf"},
        ],
    },
    "112_4": {
        "arabic": "وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",
        "latin":  "walam yakul lahu kufuwan ahad",
        "id":     "dan tidak ada sesuatu yang setara dengan Dia.",
        "rules": [
            {"kata": "لَّهُ",     "hukum": "idgham_bila", "tip": "Idgham bilaghunnah — lam bertemu lam"},
            {"kata": "كُفُوًا",   "hukum": "ghunnah",    "tip": "Tanwin — dengung 2 harakat"},
        ],
    },
    "113_1": {
        "arabic": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ",
        "latin":  "qul aud zu birabbil falaq",
        "id":     "Katakanlah: Aku berlindung kepada Tuhan yang menguasai subuh,",
        "rules": [
            {"kata": "الْفَلَقِ", "hukum": "qalqalah",    "tip": "Qaf — qalqalah sughra di tengah"},
        ],
    },
    "113_5": {
        "arabic": "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",
        "latin":  "wamin sharri hasidin idza hasad",
        "id":     "dan dari kejahatan orang yang dengki apabila dia dengki.",
        "rules": [
            {"kata": "شَرِّ",     "hukum": "tafkhim",    "tip": "Syin — huruf isti'la samar, agak tebal"},
        ],
    },
    "114_1": {
        "arabic": "قُلْ أَعُوذُ بِرَبِّ النَّاسِ",
        "latin":  "qul audzu birabbin nas",
        "id":     "Katakanlah: Aku berlindung kepada Tuhan manusia,",
        "rules": [
            {"kata": "النَّاسِ",  "hukum": "ghunnah",    "tip": "Nun tasydid — ghunnah 2 harakat"},
        ],
    },
    "114_6": {
        "arabic": "مِنَ الْجِنَّةِ وَالنَّاسِ",
        "latin":  "minal jinnati wan nas",
        "id":     "dari (golongan) jin dan manusia.",
        "rules": [
            {"kata": "الْجِنَّةِ","hukum": "ghunnah",    "tip": "Nun tasydid — ghunnah 2 harakat"},
            {"kata": "وَالنَّاسِ","hukum": "ghunnah",    "tip": "Nun tasydid — ghunnah 2 harakat"},
        ],
    },
}

# ── Deskripsi hukum tajwid ────────────────────────────
TAJWID_INFO = {
    "mad_thabii":   {"nama":"Mad Thabii","panjang":"2 harakat","cara":"Panjangkan 2 ketukan. Jangan diperpendek."},
    "mad_wajib":    {"nama":"Mad Wajib Muttashil","panjang":"4–5 harakat (WAJIB)","cara":"Wajib 4-5 ketukan. Mad bertemu hamzah satu kata."},
    "mad_lazim":    {"nama":"Mad Lazim","panjang":"6 harakat (WAJIB)","cara":"Wajib tepat 6 ketukan. Mad bertemu tasydid."},
    "ghunnah":      {"nama":"Ghunnah","panjang":"2 harakat dari hidung","cara":"Dengungkan 2 ketukan dari rongga hidung."},
    "ikhfa":        {"nama":"Ikhfa Haqiqi","panjang":"2 harakat samar","cara":"Samarkan antara jelas dan lebur, tetap dengung."},
    "ikhfa_syafawi":{"nama":"Ikhfa Syafawi","panjang":"2 harakat samar bibir","cara":"Mim samar, bibir hampir rapat, dengung 2 harakat."},
    "idgham":       {"nama":"Idgham Bighunnah","panjang":"dengung 2 harakat","cara":"Lebur ke huruf berikutnya DENGAN dengung."},
    "idgham_bila":  {"nama":"Idgham Bilaghunnah","panjang":"tanpa dengung","cara":"Lebur ke huruf berikutnya TANPA dengung."},
    "iqlab":        {"nama":"Iqlab","panjang":"2 harakat mim samar","cara":"Ubah nun → mim samar dengan dengung. Bibir hampir bertemu."},
    "qalqalah":     {"nama":"Qalqalah","panjang":"pantulan huruf","cara":"Pantulkan huruf saat sukun/waqaf. Lebih kuat di akhir ayat."},
    "tafkhim":      {"nama":"Tafkhim (Tebal)","panjang":"sifat huruf","cara":"Angkat pangkal lidah ke langit-langit belakang. Suara berat."},
    "tarqiq":       {"nama":"Tarqiq (Tipis)","panjang":"sifat huruf","cara":"Jangan angkat lidah. Suara ringan dan tipis."},
    "izhar":        {"nama":"Izhar Halqi","panjang":"jelas, tanpa dengung","cara":"Baca jelas total dari tenggorokan. Tidak ada dengung."},
    "izhar_syafawi":{"nama":"Izhar Syafawi","panjang":"jelas dari bibir","cara":"Baca mim jelas dari bibir. Bibir rapat sempurna lalu lepas."},
}


# ═══════════════════════════════════════════════════
# ANALISIS HELPER
# ═══════════════════════════════════════════════════

HARAKAT = "ًٌٍَُِّْٓ"

def strip_harakat(text: str) -> str:
    for h in HARAKAT:
        text = text.replace(h, "")
    text = re.sub(r"[أإآ]", "ا", text)
    return " ".join(text.split()).strip()

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def word_diff(transcribed: str, reference: str) -> dict:
    tw = transcribed.lower().split()
    rw = reference.lower().split()
    matched, missed = 0, []
    for i, r in enumerate(rw):
        if i < len(tw):
            s = similarity(tw[i], r)
            if s >= 0.72:
                matched += 1
            else:
                missed.append({"expected": r, "got": tw[i], "sim": round(s, 2)})
        else:
            missed.append({"expected": r, "got": "—", "sim": 0.0})
    return {
        "matched": matched,
        "total": max(len(rw), 1),
        "missed": missed,
        "pct": round(matched / max(len(rw), 1) * 100),
    }

def make_score(wd: dict, sim: float) -> int:
    return max(0, min(100, int(wd["pct"] * 0.6 + sim * 100 * 0.4)))

def build_feedback(key: str, wd: dict, score: int) -> dict:
    data    = QURAN[key]
    rules   = data["rules"]
    missed  = wd["missed"][:3]
    items   = []
    tts_parts = []

    for miss in missed:
        exp = miss["expected"]
        got = miss["got"]
        sim = miss["sim"]
        rule = next(
            (r for r in rules if strip_harakat(r["kata"]) in exp or exp in strip_harakat(r["kata"])),
            None
        )
        if rule:
            info = TAJWID_INFO.get(rule["hukum"], {})
            nama = info.get("nama", rule["hukum"])
            cara = info.get("cara", "")
            items.append({"kata": rule["kata"], "hukum": nama, "perbaikan": cara})
            if sim < 0.5:
                tts_parts.append(f"Ulangi kata {rule['kata']}. Hukumnya {nama}, {cara}.")
            else:
                tts_parts.append(f"Pada kata {rule['kata']}, perhatikan {nama}. {cara}.")
        else:
            if got and got != "—":
                tts_parts.append(f"Kata yang terdengar {got} seharusnya {exp}. Perhatikan makhraj hurufnya.")

    if not items:
        if score >= 95:
            tts_parts.append("Masya Allah, bacaan sangat sempurna! Pertahankan kualitas ini.")
        elif score >= 85:
            tts_parts.append("Sangat baik! Bacaan sudah benar. Latih terus untuk semakin lancar.")
        elif score >= 75:
            tts_parts.append("Bagus! Ada sedikit yang perlu diperbaiki. Dengarkan contoh qori dan ikuti.")
        else:
            tts_parts.append("Bacaan perlu ditingkatkan. Dengarkan contoh qori dan ulangi perlahan.")

    return {
        "tts_text": " ".join(tts_parts),
        "corrections": items,
        "rules_in_ayah": [
            {
                "kata": r["kata"],
                "hukum": TAJWID_INFO.get(r["hukum"], {}).get("nama", r["hukum"]),
                "tip": r["tip"],
                "panjang": TAJWID_INFO.get(r["hukum"], {}).get("panjang", ""),
            }
            for r in rules
        ],
    }

def grade(score: int) -> str:
    if score >= 95: return "Sempurna 🌟"
    if score >= 85: return "Sangat Baik ✨"
    if score >= 75: return "Bagus 👍"
    if score >= 60: return "Cukup 📖"
    return "Perlu Latihan 💪"


# ═══════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page HTML ringan."""
    count = len(QURAN)
    configured = "✅ Aktif" if OPENAI_KEY else "❌ Belum dikonfigurasi"
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NurAI API</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0a1f12;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}
.card{{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:40px;max-width:480px;width:100%;text-align:center}}
.logo{{font-size:48px;margin-bottom:12px}}
h1{{font-size:28px;font-weight:700;margin-bottom:4px}}
h1 span{{color:#e8c96a}}
.sub{{font-size:14px;color:rgba(255,255,255,.5);margin-bottom:28px}}
.status{{background:rgba(255,255,255,.06);border-radius:12px;padding:16px;margin-bottom:20px;text-align:left}}
.row{{display:flex;justify-content:space-between;padding:5px 0;font-size:13px;border-bottom:1px solid rgba(255,255,255,.06)}}
.row:last-child{{border-bottom:none}}
.lbl{{color:rgba(255,255,255,.5)}}
.val{{font-weight:600;color:#6ee7a0}}
.val.warn{{color:#fcd34d}}
.btns{{display:flex;gap:10px;justify-content:center}}
.btn{{padding:10px 24px;border-radius:50px;font-size:13px;font-weight:600;text-decoration:none;transition:.2s}}
.btn-green{{background:#2a7a4c;color:#fff}}
.btn-outline{{background:transparent;border:1px solid rgba(255,255,255,.2);color:#fff}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🕌</div>
  <h1>Nur<span>AI</span></h1>
  <div class="sub">نُورُ القُرآنِ فِي يَدَيكَ · Tajwid Analysis API</div>
  <div class="status">
    <div class="row"><span class="lbl">Status</span><span class="val">✅ Online</span></div>
    <div class="row"><span class="lbl">OpenAI Whisper</span><span class="val {'val' if OPENAI_KEY else 'val warn'}">{configured}</span></div>
    <div class="row"><span class="lbl">Ayat tersedia</span><span class="val">{count} ayat</span></div>
    <div class="row"><span class="lbl">Platform</span><span class="val">Hugging Face Spaces</span></div>
    <div class="row"><span class="lbl">Port</span><span class="val">7860</span></div>
  </div>
  <div class="btns">
    <a href="/docs" class="btn btn-green">📖 API Docs</a>
    <a href="/health" class="btn btn-outline">💚 Health</a>
  </div>
</div>
</body>
</html>"""


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "platform": "huggingface-spaces",
        "openai_configured": bool(OPENAI_KEY),
        "whisper_model": WHISPER_MODEL,
        "ayahs_loaded": len(QURAN),
        "version": "2.0.0",
    }


@app.get("/ayahs")
async def list_ayahs():
    return {
        "total": len(QURAN),
        "ayahs": [
            {
                "key": k,
                "surah": int(k.split("_")[0]),
                "ayah": int(k.split("_")[1]),
                "arabic": v["arabic"],
                "id": v["id"],
                "rules_count": len(v["rules"]),
            }
            for k, v in QURAN.items()
        ],
    }


@app.post("/analyze")
async def analyze(
    audio: UploadFile = File(..., description="Audio rekaman: webm/mp3/wav/ogg — maks 10MB"),
    surah: str        = Form(..., description="Nomor surah, contoh: 1"),
    ayah:  str        = Form(..., description="Nomor ayat, contoh: 7"),
):
    """
    **Analisis bacaan Al-Qur'an.**

    Kirim rekaman audio → dapat:
    - Skor 0–100 (berdasarkan transkripsi Whisper nyata)
    - Feedback TTS bahasa Indonesia
    - Koreksi tajwid per kata
    - Daftar hukum tajwid yang berlaku pada ayat
    """

    # ── Validasi API key ─────────────────────────────
    if not OPENAI_KEY:
        raise HTTPException(503, detail={
            "error": "OPENAI_API_KEY belum diset",
            "cara_set": "HF Space Settings → Variables and secrets → New secret → OPENAI_API_KEY"
        })

    # ── Validasi ayat ────────────────────────────────
    key = f"{surah}_{ayah}"
    if key not in QURAN:
        raise HTTPException(404, detail={
            "error": f"Ayat {surah}:{ayah} belum ada di database",
            "tersedia": list(QURAN.keys()),
            "tambah_di": "QURAN dict di main.py",
        })

    # ── Validasi ukuran ──────────────────────────────
    raw = await audio.read()
    mb  = len(raw) / 1048576
    if mb > MAX_SIZE_MB:
        raise HTTPException(413, detail=f"File {mb:.1f}MB terlalu besar. Maks {MAX_SIZE_MB}MB.")

    log.info(f"Analyzing {key} | size={mb:.2f}MB | format={audio.content_type}")

    # ── Kirim ke Whisper ─────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                files={"file": (audio.filename or f"ayah.webm", raw, audio.content_type or "audio/webm")},
                data={"model": WHISPER_MODEL, "language": "ar", "response_format": "json", "temperature": 0},
            )
    except httpx.TimeoutException:
        raise HTTPException(504, detail="Whisper timeout. Rekaman terlalu panjang atau koneksi lambat.")
    except httpx.RequestError as e:
        raise HTTPException(502, detail=f"Network error: {e}")

    if resp.status_code != 200:
        err_msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        log.error(f"Whisper error: {err_msg}")
        raise HTTPException(502, detail={"error": "Whisper API error", "whisper": err_msg})

    detected = resp.json().get("text", "").strip()
    log.info(f"Detected: '{detected}'")

    # ── Analisis ─────────────────────────────────────
    data   = QURAN[key]
    arabic = data["arabic"]
    latin  = data["latin"]

    det_clean  = strip_harakat(detected)
    ref_clean  = strip_harakat(arabic)

    sim        = similarity(det_clean, ref_clean)
    wd         = word_diff(det_clean, ref_clean)
    score      = make_score(wd, sim)
    feedback   = build_feedback(key, wd, score)

    return JSONResponse({
        "success":  True,
        "surah":    int(surah),
        "ayah":     int(ayah),
        "score":    score,
        "grade":    grade(score),
        "transcription": {
            "detected":        detected,
            "reference":       arabic,
            "reference_latin": latin,
            "similarity_pct":  round(sim * 100),
        },
        "word_analysis": {
            "accuracy_pct": wd["pct"],
            "matched":      wd["matched"],
            "total_words":  wd["total"],
            "missed_words": wd["missed"][:5],
        },
        "tajwid": {
            "tts_text":     feedback["tts_text"],
            "corrections":  feedback["corrections"],
            "rules_in_ayah":feedback["rules_in_ayah"],
        },
        "terjemah": data["id"],
    })


# ── Test endpoint tanpa audio (dev only) ─────────────
@app.get("/test/{surah}/{ayah}")
async def test_ayah(surah: int, ayah: int):
    """Cek data ayat tanpa kirim audio."""
    key = f"{surah}_{ayah}"
    if key not in QURAN:
        raise HTTPException(404, {"error": f"{surah}:{ayah} tidak ada", "tersedia": list(QURAN.keys())})
    d = QURAN[key]
    return {
        "key": key,
        "arabic": d["arabic"],
        "latin": d["latin"],
        "id": d["id"],
        "rules": [
            {**r, "info": TAJWID_INFO.get(r["hukum"], {})}
            for r in d["rules"]
        ],
    }
