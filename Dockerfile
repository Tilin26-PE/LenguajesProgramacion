# ---------- Etapa 1: compilar el JAR de Scala (autocontenido, con "sbt assembly") ----------
FROM eclipse-temurin:17-jdk-jammy AS scala-build

# Instala sbt bajando el binario directo (mas confiable que apt-key/keyservers externos)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -fL https://github.com/sbt/sbt/releases/download/v1.9.9/sbt-1.9.9.tgz \
       | tar xz -C /usr/share/ \
    && ln -s /usr/share/sbt/bin/sbt /usr/local/bin/sbt \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY scala/pedidocore/ .
RUN sbt assembly


# ---------- Etapa 2: imagen final (Python + SWI-Prolog + JRE) ----------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        swi-prolog \
        openjdk-17-jre-headless \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prolog/ ./prolog/
COPY python/ ./python/
COPY --from=scala-build /build/target/scala-2.13/pedidocore-assembly.jar \
     ./scala/pedidocore/target/scala-2.13/pedidocore-assembly.jar

WORKDIR /app/python

# Render define $PORT en tiempo de ejecucion; 10000 es solo un valor por defecto.
ENV PORT=10000
EXPOSE 10000

CMD gunicorn -w 2 -b 0.0.0.0:$PORT app:app
