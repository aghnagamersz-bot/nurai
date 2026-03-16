# ── Hugging Face Spaces — NurAI Whisper API ──────────
# Catatan penting HF Spaces:
#   - Port WAJIB 7860
#   - Run sebagai non-root user (user ID 1000)
#   - Hanya /tmp yang writable
#   - Cache semua library ke /tmp

FROM python:3.11-slim

# ── Buat non-root user (WAJIB di HF Spaces) ──────────
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# ── Set semua cache ke /tmp (WAJIB di HF Spaces) ─────
ENV HF_HOME=/tmp/hf-cache
ENV TRANSFORMERS_CACHE=/tmp/hf-cache
ENV TOKENIZERS_PARALLELISM=false
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Install dependencies ──────────────────────────────
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# ── Copy source code ──────────────────────────────────
COPY --chown=user . /app

# ── Port 7860 — WAJIB untuk HF Spaces ────────────────
EXPOSE 7860

# ── Start server ──────────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
