# ============================================================
# Timba Predictor v2.2 - Dockerfile Multi-Stage Optimizado
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar dependencias del sistema para compilar extensiones C/Cython
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     gcc     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
# Etapa Final de Ejecución (Runtime)
# ============================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Instalar librerías mínimas de runtime
RUN apt-get update && apt-get install -y --no-install-recommends     sqlite3     curl     && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados desde la etapa builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:/home/nahuel/.gemini/antigravity-cli/bin:/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/lib/jvm/default/bin:/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Crear usuario sin privilegios por seguridad
RUN useradd -m -u 1000 timbauser &&     mkdir -p /app/data/databases /app/data/flask_cache /app/logs &&     chown -R timbauser:timbauser /app

# Copiar código fuente
COPY --chown=timbauser:timbauser . /app

USER timbauser

# Compilar módulo Cython si setup.py está disponible
RUN python setup.py build_ext --inplace || true

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3     CMD curl -f http://localhost:5000/api/v1/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
