FROM python:3.11-alpine@sha256:cd04730b8511def3fbf14204d66a0c1536f290b8e896ed5a94cd64cb15ac1356 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-alpine@sha256:cd04730b8511def3fbf14204d66a0c1536f290b8e896ed5a94cd64cb15ac1356
WORKDIR /app

COPY --from=builder /root/.local /usr/local
COPY app.py .

RUN addgroup -g 10001 appgroup \
    && adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser \
    && chown -R 10001:10001 /app

ENV HOME=/app
USER 10001:10001

EXPOSE 7100

# wget BusyBox plutot que python+urllib : ce dernier coutait ~0,5 s de CPU par
# passage (soit ~2 % de CPU permanent sur le NAS).
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:7100/health

CMD ["gunicorn", "-w", "1", "--worker-class", "gthread", "--threads", "4", "-b", "0.0.0.0:7100", "app:app"]