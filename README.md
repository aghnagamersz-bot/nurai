---
title: NurAI Whisper API
emoji: 🕌
colorFrom: green
colorTo: yellow
sdk: docker
pinned: true
license: mit
short_description: Analisis tajwid Al-Quran via OpenAI Whisper — NurAI Backend
---

# 🕌 NurAI — Whisper Tajwid API

Backend FastAPI untuk aplikasi **NurAI** — platform belajar Al-Qur'an dengan analisis tajwid otomatis menggunakan OpenAI Whisper.

## Endpoints

| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/` | Info API |
| `GET` | `/health` | Status server & OpenAI |
| `GET` | `/ayahs` | Daftar ayat tersedia |
| `POST` | `/analyze` | **Analisis bacaan** — kirim audio, dapat skor + feedback |

## Cara pakai `/analyze`

```bash
curl -X POST https://YOUR-USERNAME-nurai-whisper.hf.space/analyze \
  -F "audio=@bismillah.webm" \
  -F "surah=1" \
  -F "ayah=1"
```

## Response contoh

```json
{
  "success": true,
  "score": 87,
  "grade": "Sangat Baik",
  "transcription": {
    "detected": "بسم الله الرحمن الرحيم",
    "similarity_pct": 92
  },
  "tajwid": {
    "tts_text": "Bagus! Mad Thabii pada kata اللَّهِ sudah tepat 2 harakat.",
    "corrections": [],
    "rules_present": [...]
  }
}
```

## Setup

Set environment variable `OPENAI_API_KEY` di Settings → Variables → New Secret.

## Docs interaktif

Buka `/docs` untuk Swagger UI lengkap.
