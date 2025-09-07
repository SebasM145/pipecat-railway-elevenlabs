# Imagen base oficial con Python y uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm

# Instalar dependencias de audio y certificados
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copiar definiciones de dependencias primero (para cache)
COPY pyproject.toml uv.lock* ./

# Instalar dependencias del proyecto
RUN uv sync --no-dev

# Copiar el resto del código
COPY . .

# Exponer el puerto que usa el bot (7860 por defecto en quickstart)
EXPOSE 7860

# Comando de arranque
CMD ["bash", "-lc", "uv run python bot.py --host 0.0.0.0 --port ${PORT:-8080} --transport daily"]

# --- Alternativa si tu bot requiere host/port explícitos ---
# CMD ["bash", "-lc", "uv run python bot.py --host 0.0.0.0 --port ${PORT:-7860}"]
