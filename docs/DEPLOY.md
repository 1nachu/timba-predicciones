# Guía de Despliegue en Producción (v3.0 — Next.js SSR + Nginx)

A partir de la versión **3.0**, el tráfico público es atendido por **Next.js (SSR)** en el puerto `:3000`. El servidor **Flask API (`:5000`)** queda aislado dentro de la red interna de Docker (`timba-network`) y **no expone su puerto al host**. Next.js actúa como proxy reverso de `/api/*` hacia `http://web:5000/api/*`.

---

## 1. Configuración de Nginx (Reverse Proxy)

Edita el bloque de servidor de Nginx (por ejemplo en `/etc/nginx/sites-available/timba-predictor`) para apuntar el `proxy_pass` a `http://127.0.0.1:3000` en lugar de `127.0.0.1:5000`:

```nginx
server {
    listen 80;
    server_name futbol-predicciones.xyz www.futbol-predicciones.xyz;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name futbol-predicciones.xyz www.futbol-predicciones.xyz;

    ssl_certificate     /etc/letsencrypt/live/futbol-predicciones.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/futbol-predicciones.xyz/privkey.pem;

    # Compresión Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # Cache inmutable para assets estáticos compilados de Next.js
    location /_next/static/ {
        proxy_pass http://127.0.0.1:3000;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # Tráfico principal (SSR + API /api/v1/*)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Valida y recarga Nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 2. Levantar los Contenedores

```bash
docker compose up -d --build
```

---

## 3. Checklist Post-Deploy

1. **Verificar estado de contenedores:**
   ```bash
   docker compose ps
   ```
   Tanto `timba-web` como `timba-frontend` deben figurar como `healthy`.

2. **Verificar que la API responde a través del proxy de Next.js / Nginx:**
   ```bash
   curl -f https://futbol-predicciones.xyz/api/v1/health
   ```

3. **Verificar que el puerto `:5000` está cerrado hacia el exterior:**
   ```bash
   curl http://127.0.0.1:5000/api/v1/health
   ```
   *(Debe devolver `Connection refused`).* Si tenías una regla en `ufw` o firewall abriendo el puerto `5000/tcp`, elimínala:
   ```bash
   sudo ufw delete allow 5000/tcp
   ```
