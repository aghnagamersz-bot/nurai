# 🚀 NurAI — Deploy ke Hugging Face Spaces
## Panduan Lengkap Step-by-Step (30 Menit, $0)

---

## ✅ Yang Kamu Butuhkan

- [ ] Akun GitHub (gratis) → github.com/signup
- [ ] Akun Hugging Face (gratis) → huggingface.co/join
- [ ] OpenAI API Key → platform.openai.com (kredit $5 gratis untuk akun baru)
- [ ] Git terinstall di laptop (`git --version` untuk cek)

---

## BAGIAN 1 — PERSIAPAN GITHUB (10 menit)

### Step 1 — Buat repository baru di GitHub

1. Buka **github.com** → klik **"+"** di pojok kanan atas → **"New repository"**
2. Isi:
   - **Repository name**: `nurai-whisper-api`
   - **Description**: `NurAI Quran Tajwid Analysis API`
   - Pilih **Public**
   - ✅ Centang **"Add a README file"**
3. Klik **"Create repository"**

### Step 2 — Clone & isi file

Buka terminal / command prompt:

```bash
# Clone repo kosong
git clone https://github.com/USERNAME_KAMU/nurai-whisper-api.git
cd nurai-whisper-api

# Copy semua file dari folder nurai-hf ke sini:
# - main.py
# - requirements.txt
# - Dockerfile
# - README.md  (TIMPA yang sudah ada)
# - whisper-client-hf.js
```

### Step 3 — Push ke GitHub

```bash
git add .
git commit -m "NurAI Whisper API - initial deploy"
git push origin main
```

Refresh github.com → pastikan semua file terlihat ✅

---

## BAGIAN 2 — BUAT HUGGING FACE SPACE (5 menit)

### Step 4 — Buat akun HF

1. Buka **huggingface.co/join**
2. Daftar dengan email atau GitHub
3. Verifikasi email

### Step 5 — Buat Space baru

1. Buka **huggingface.co/spaces**
2. Klik tombol **"Create new Space"** (pojok kanan atas)
3. Isi form:

   | Field | Isi |
   |-------|-----|
   | **Owner** | Username kamu |
   | **Space name** | `nurai-whisper` |
   | **License** | MIT |
   | **SDK** | **Docker** ← PENTING! |
   | **Docker template** | Blank |
   | **Visibility** | Public (gratis) |

4. Klik **"Create Space"**

> ⚠️ Pastikan pilih **Docker** bukan Gradio/Streamlit!

---

## BAGIAN 3 — SAMBUNGKAN GITHUB KE HF SPACE (5 menit)

### Step 6 — Dapatkan HF Token

1. Buka **huggingface.co/settings/tokens**
2. Klik **"New token"**
3. Nama: `nurai-deploy`, Role: **Write**
4. Klik **"Generate token"**
5. **COPY token** — hanya ditampilkan sekali! (format: `hf_xxxxxxxxxxxx`)

### Step 7 — Push code ke HF Space

Di terminal, di dalam folder `nurai-whisper-api`:

```bash
# Tambahkan HF Space sebagai remote kedua
git remote add hf https://huggingface.co/spaces/USERNAME_HF_KAMU/nurai-whisper

# Push ke HF Space (akan minta password → masukkan HF Token)
git push hf main
```

Saat diminta **Password**: paste HF Token kamu (`hf_xxxx`)

> 💡 Jika pakai Windows dan git credential manager, token akan tersimpan otomatis

### Step 8 — Monitor build

1. Buka **huggingface.co/spaces/USERNAME/nurai-whisper**
2. Lihat tab **"Logs"** untuk monitor build
3. Build pertama ~3–5 menit
4. Status akan berubah: Building → Running

---

## BAGIAN 4 — SET OPENAI API KEY (3 menit)

### Step 9 — Dapatkan OpenAI API Key

1. Buka **platform.openai.com**
2. Daftar/Login → klik nama profil → **"API Keys"**
3. Klik **"Create new secret key"**
4. Nama: `NurAI`, klik **Create**
5. **COPY key** — format: `sk-proj-xxxxx`

> 🎁 Akun baru otomatis dapat **$5 kredit gratis** = 833 menit Whisper!

### Step 10 — Set Secret di HF Space

1. Buka Space kamu → tab **"Settings"**
2. Scroll ke **"Variables and secrets"**
3. Klik **"New secret"**:
   - **Name**: `OPENAI_API_KEY`
   - **Value**: paste `sk-proj-xxxxx`
4. Klik **"Save"**
5. Space akan **restart otomatis** dengan key baru

---

## BAGIAN 5 — SAMBUNGKAN KE NURAI APP (5 menit)

### Step 11 — Update whisper-client-hf.js

Buka file `whisper-client-hf.js`, ganti baris ini:

```javascript
// SEBELUM:
const HF_API = "https://YOUR_USERNAME-nurai-whisper.hf.space";

// SESUDAH (contoh):
const HF_API = "https://ahmad123-nurai-whisper.hf.space";
```

> Format URL: `https://USERNAME_HF-SPACENAME.hf.space`
> Username dan spacename dipisah tanda `-`

### Step 12 — Tambahkan ke NurAI-App.html

Buka `NurAI-App.html` di text editor, sebelum `</body>` tambahkan:

```html
<!-- Whisper API Client — taruh sebelum </body> -->
<script src="whisper-client-hf.js"></script>
```

### Step 13 — Ganti tombol rekam

Di `NurAI-App.html`, cari dan ganti:

```html
<!-- CARI: -->
<button class="rec-big" id="recBtn" onclick="toggleRec()">

<!-- GANTI DENGAN: -->
<button class="rec-big" id="recBtn" onclick="toggleRecReal()">
```

Dan untuk tombol rekam per ayat, di fungsi `renderAyahs()` cari:
```javascript
// CARI:
onclick="recAyah(${a.num})"

// GANTI:
onclick="recAyahReal(S.curSurah, ${a.num})"
```

---

## BAGIAN 6 — CEKLIS PENGECEKAN MANUAL

### ✅ Cek 1 — Backend hidup

Buka di browser:
```
https://USERNAME-nurai-whisper.hf.space
```
**Harus muncul:** Halaman hijau gelap dengan status ✅ Online

---

### ✅ Cek 2 — OpenAI terkonfigurasi

Buka:
```
https://USERNAME-nurai-whisper.hf.space/health
```
**Harus muncul:**
```json
{
  "status": "ok",
  "openai_configured": true,
  "ayahs_loaded": 14
}
```

Jika `openai_configured: false` → ulangi Step 10.

---

### ✅ Cek 3 — API Docs berjalan

Buka:
```
https://USERNAME-nurai-whisper.hf.space/docs
```
**Harus muncul:** Swagger UI dengan 5 endpoint (/, /health, /ayahs, /analyze, /test/{surah}/{ayah})

---

### ✅ Cek 4 — Test data ayat

Buka:
```
https://USERNAME-nurai-whisper.hf.space/test/1/7
```
**Harus muncul:** JSON dengan data Ayat 7 Al-Fatihah + 3 hukum tajwid

---

### ✅ Cek 5 — Test Whisper via Swagger UI

1. Buka `/docs`
2. Klik `POST /analyze` → **"Try it out"**
3. Upload file audio (rekam bismillah dulu, simpan sebagai `.webm` atau `.mp3`)
4. Isi `surah: 1`, `ayah: 1`
5. Klik **"Execute"**

**Harus muncul response:**
```json
{
  "success": true,
  "score": 82,
  "grade": "Sangat Baik ✨",
  "transcription": {
    "detected": "بسم الله الرحمن الرحيم",
    "similarity_pct": 88
  },
  "tajwid": {
    "tts_text": "Bagus! Mad Thabii sudah tepat...",
    "corrections": [],
    "rules_in_ayah": [...]
  }
}
```

Jika skor **0** dan `detected` kosong → kualitas audio buruk atau format tidak support.

---

### ✅ Cek 6 — Test dari NurAI App

1. Buka NurAI-App.html di browser (**harus dari https://** — deploy ke Netlify dulu)
2. Buka Console (F12 → Console)
3. **Harus muncul:** `✅ NurAI Whisper API online: https://...`
4. Tap Rekam → izinkan mikrofon → bacakan ayat
5. Tunggu 3–5 detik setelah stop
6. **Harus muncul:** modal skor dengan skor nyata (bukan random) + transkripsi + feedback TTS

---

### ✅ Cek 7 — TTS feedback berbahasa Indonesia

Setelah rekam dan skor muncul:
- Dengarkan speaker laptop/HP
- **Harus terdengar suara** dalam bahasa Indonesia
- Contoh: *"Pada kata اللَّهِ, perhatikan Mad Thabii. Panjangkan 2 ketukan."*

Jika tidak ada suara → cek volume, pastikan browser izinkan autoplay audio.

---

## ⚠️ TROUBLESHOOTING

### Build gagal di HF Spaces
```
❌ Error: ... permission denied
```
**Solusi:** Pastikan Dockerfile pakai non-root user (sudah ada di file kita).

### CORS error di browser console
```
❌ Access-Control-Allow-Origin
```
**Solusi:** `allow_origins=["*"]` sudah ada di kode. Pastikan fetch ke `https://` bukan `http://`.

### Whisper error "invalid file format"
**Solusi:** WebM dari Chrome biasanya OK. Safari pakai MP4 — sudah di-handle di client.

### Space status "Sleeping"
HF Spaces gratis bisa tidur setelah beberapa hari tidak aktif.
**Solusi:** Klik "Restart this Space" di halaman Space.
Berbeda dengan Render — wake-up HF hanya ~10 detik, bukan 60 detik!

### Score selalu rendah (0–30)
**Kemungkinan:**
- Rekam terlalu jauh dari mikrofon
- Ada noise/kebisingan
- Format audio tidak kompatibel

**Debug:** Buka `/docs` → test manual dengan file audio yang jelas.

---

## 📊 MONITORING BIAYA OPENAI

Cek pemakaian di: **platform.openai.com/usage**

| Durasi rekaman | Biaya Whisper |
|----------------|---------------|
| 1 menit | $0.006 |
| 1 jam | $0.36 |
| Kredit $5 | ~833 menit |

Notifikasi otomatis saat kredit hampir habis via email OpenAI.

---

## 🔄 UPDATE KODE

Setiap kali ada perubahan kode:

```bash
# Di folder nurai-whisper-api
git add .
git commit -m "Update: deskripsi perubahan"
git push hf main  # Push ke HF Space
# HF Space otomatis rebuild dalam 2-3 menit
```

---

## 🎯 URL FINAL

Setelah semua selesai:

| Resource | URL |
|----------|-----|
| Backend API | `https://USERNAME-nurai-whisper.hf.space` |
| API Docs | `https://USERNAME-nurai-whisper.hf.space/docs` |
| Health check | `https://USERNAME-nurai-whisper.hf.space/health` |
| NurAI App | Deploy ke `https://USERNAME.netlify.app` |

---

*NurAI — نُورُ القُرآنِ فِي يَدَيكَ · We will fly to the moon 🚀🌙*
