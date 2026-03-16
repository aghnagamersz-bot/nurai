/**
 * NurAI — Whisper Client (Hugging Face Spaces Edition)
 * =====================================================
 * Tambahkan ke NurAI-App.html sebelum </body>:
 *   <script src="whisper-client-hf.js"></script>
 *
 * Lalu ganti:
 *   onclick="toggleRec()"   →  onclick="toggleRecReal()"
 *   onclick="recAyah(N)"    →  onclick="recAyahReal(S.curSurah, N)"
 */

// ── GANTI dengan URL Space kamu ───────────────────────
// Format: https://USERNAME-SPACENAME.hf.space
const HF_API = "https://YOUR_USERNAME-nurai-whisper.hf.space";
// Contoh: "https://ahmad-nurai-whisper.hf.space"

// ── State ─────────────────────────────────────────────
let _recorder   = null;
let _chunks     = [];
let _stream     = null;
let _recActive  = false;
let _recSurah   = 1;
let _recAyah    = 1;

// ── CEK API ONLINE ────────────────────────────────────
async function whisperOnline() {
  try {
    const r = await fetch(`${HF_API}/health`, { signal: AbortSignal.timeout(8000) });
    const d = await r.json();
    return d.status === "ok" && d.openai_configured;
  } catch { return false; }
}

// ── MULAI REKAM ───────────────────────────────────────
async function recAyahReal(surahNum, ayahNum) {
  const ok = await whisperOnline();
  if (!ok) {
    // Fallback ke simulasi jika API tidak tersedia
    console.warn("⚠ Whisper API offline → simulasi");
    toast("Mode Simulasi", "Backend Whisper belum tersedia. Skor adalah estimasi.");
    if (typeof recAyah === "function") recAyah(ayahNum);
    return;
  }

  // Minta izin mikrofon
  try {
    _stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true }
    });
  } catch (err) {
    if (err.name === "NotAllowedError")
      toast("Mikrofon Ditolak", "Izinkan akses mikrofon di browser untuk merekam.");
    else
      toast("Error Mikrofon", err.message);
    return;
  }

  _chunks    = [];
  _recActive = true;
  _recSurah  = surahNum;
  _recAyah   = ayahNum;

  // Pilih format terbaik yang didukung browser
  const mime =
    MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" :
    MediaRecorder.isTypeSupported("audio/webm")             ? "audio/webm" :
    MediaRecorder.isTypeSupported("audio/mp4")              ? "audio/mp4" : "audio/ogg";

  _recorder = new MediaRecorder(_stream, { mimeType: mime });
  _recorder.ondataavailable = e => { if (e.data.size > 0) _chunks.push(e.data); };
  _recorder.start(100);

  // Update UI
  S.curAyah = ayahNum;
  document.querySelectorAll(".ab").forEach(x => x.classList.remove("rec-on"));
  const el = document.getElementById("ab" + ayahNum);
  if (el) el.classList.add("rec-on");
  document.getElementById("recBtn").classList.add("on");
  document.getElementById("waveEl").classList.add("on");
  document.getElementById("recLbl").textContent = `🔴 Merekam Ayat ${ayahNum}...`;
  document.getElementById("recSub").textContent = "Tap tombol untuk berhenti & analisis";

  // Auto-stop setelah 15 detik (satu ayat biasanya <10 detik)
  setTimeout(() => { if (_recActive) toggleRecReal(); }, 15000);
}

// ── STOP + ANALISIS ───────────────────────────────────
async function toggleRecReal() {
  // Jika belum rekam → mulai rekam
  if (!_recActive) {
    await recAyahReal(S.curSurah, S.curAyah);
    return;
  }

  // Stop recording
  _recActive = false;
  document.getElementById("recBtn").classList.remove("on");
  document.getElementById("waveEl").classList.remove("on");
  document.getElementById("recLbl").textContent = "⏳ Whisper menganalisis...";
  document.getElementById("recSub").textContent = "Biasanya 2–4 detik · Harap tunggu";

  const result = await new Promise(resolve => {
    _recorder.onstop = async () => {
      // Hentikan mikrofon
      _stream?.getTracks().forEach(t => t.stop());
      _stream = null;

      const blob = new Blob(_chunks, { type: _recorder.mimeType || "audio/webm" });
      try {
        resolve(await _callWhisper(blob, _recSurah, _recAyah));
      } catch (err) {
        console.error("Whisper call failed:", err);
        toast("Analisis Gagal", err.message || "Coba lagi atau periksa koneksi.");
        resolve(null);
      }
    };
    _recorder.stop();
  });

  // Reset label jika gagal
  if (!result) {
    document.getElementById("recLbl").textContent = `Rekam Ayat ${S.curAyah}`;
    document.getElementById("recSub").textContent = "Tekan mikrofon untuk mulai rekam";
    return;
  }

  // ── Proses hasil ─────────────────────────────────
  const { score, tajwid, word_analysis, transcription, grade: g } = result;
  const ayah = _recAyah;

  // Simpan skor
  S.scores[ayah] = score;
  if (!S.hafalan[ayah]) S.hafalan[ayah] = { c: 0 };
  if (score >= 75) {
    S.hafalan[ayah].c = Math.min(3, S.hafalan[ayah].c + 1);
  } else {
    S.errors.unshift({
      surah: SURAHS.find(x => x.n === S.curSurah)?.name || "—",
      ayah, sc: score,
      time: new Date().toLocaleTimeString("id-ID"),
      rules: tajwid?.rules_in_ayah?.map(r => r.hukum) || [],
    });
    if (S.errors.length > 50) S.errors.pop();
  }

  // Save ke Firestore
  if (typeof saveScoreToFirestore === "function") {
    const name = SURAHS.find(x => x.n === S.curSurah)?.name;
    saveScoreToFirestore(name, ayah, score);
  }

  // TTS feedback nyata dari Whisper
  const ttsText = tajwid?.tts_text || "";
  if (ttsText && "speechSynthesis" in window) {
    const u = new SpeechSynthesisUtterance(ttsText);
    u.lang = "id-ID"; u.rate = 0.92;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  // Next ayah
  const ayahs  = typeof getAyahs === "function" ? getAyahs() : [];
  const nextN  = ayah < ayahs.length ? ayah + 1 : 1;
  S.curAyah = nextN;
  document.getElementById("recLbl").textContent = `Rekam Ayat ${nextN}`;
  document.getElementById("recSub").textContent = "Tekan mikrofon · TTS aktif";

  renderAyahs();

  // Tampilkan modal skor
  setTimeout(() => _showScoreModal(ayah, result), 500);
}

// ── KIRIM KE HF WHISPER API ───────────────────────────
async function _callWhisper(blob, surah, ayah) {
  const form = new FormData();
  form.append("audio", blob, `nurai_${surah}_${ayah}.webm`);
  form.append("surah", String(surah));
  form.append("ayah",  String(ayah));

  const ctrl    = new AbortController();
  const timeout = setTimeout(() => ctrl.abort(), 35000);

  try {
    const res = await fetch(`${HF_API}/analyze`, {
      method: "POST", body: form, signal: ctrl.signal
    });
    clearTimeout(timeout);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.error || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === "AbortError") throw new Error("Timeout — coba rekaman lebih pendek");
    throw err;
  }
}

// ── MODAL SKOR DENGAN TRANSKRIPSI ─────────────────────
function _showScoreModal(ayah, result) {
  const { score, grade: g, transcription: tr, word_analysis: wa, tajwid } = result;

  document.getElementById("scNum").textContent   = score;
  document.getElementById("scTitle").textContent =
    score >= 95 ? "Sempurna! 🌟" : score >= 85 ? "Sangat Baik! ✨" :
    score >= 75 ? "Bagus! 👍"    : score >= 60 ? "Cukup 📖" : "Perlu Latihan 💪";
  document.getElementById("scSub").textContent =
    `Ayat ${ayah} · ${SURAHS.find(x => x.n === S.curSurah)?.name || ""}`;
  document.getElementById("sb1").textContent = `${wa.accuracy_pct}%`;
  document.getElementById("sb2").textContent = `${wa.matched}/${wa.total_words} kata`;
  document.getElementById("sb3").textContent = `${tr.similarity_pct}%`;
  document.getElementById("sb4").textContent = g;

  // Feedback + transkripsi
  let fb = tajwid?.tts_text || "";
  if (tr?.detected) fb += `\n\n📝 Terdengar: "${tr.detected}"`;
  const corr = tajwid?.corrections || [];
  if (corr.length)
    fb += "\n\n🔍 " + corr.map(c => `${c.kata}: ${c.hukum} — ${c.perbaikan}`).join("\n");
  document.getElementById("scFb").textContent = fb;

  // Warna ring
  const ring = document.getElementById("scRing");
  if (ring) ring.style.borderColor = score>=85?"var(--jade3)":score>=60?"#f0c030":"#dc2626";
  const num = document.getElementById("scNum");
  if (num) num.style.color = score>=85?"var(--jade2)":score>=60?"#92600a":"#b91c1c";

  document.getElementById("scModal").classList.add("open");
}

// ── AUTO CEK saat load ────────────────────────────────
(async () => {
  const ok = await whisperOnline();
  console.log(ok
    ? `✅ NurAI Whisper API online: ${HF_API}`
    : `⚠ Whisper API offline — mode simulasi aktif`
  );
})();
