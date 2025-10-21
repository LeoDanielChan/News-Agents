# News Agents — Instrucciones para Docker Compose

Este proyecto contiene usa API FastAPI que puede ejecutarse con Docker Compose tanto en modo desarrollo como en producción.

## Requisitos

- Docker >= 20.10
- Docker Compose (la versión integrada en Docker Desktop o la CLI compatible) o `docker compose` (sin guion)
- VS Code con la extensión "Dev Containers" instalada

## Archivos importantes

- `Dockerfile` — imagen base para la aplicación
- `docker-compose.dev.yml` — configuración para desarrollo (con volúmenes y recarga)
- `docker-compose.prod.yml` — configuración para producción
- `app/` — código fuente
- `requirements.txt` — dependencias del proyecto

## Uso — Desarrollo

El archivo `docker-compose.dev.yml` está configurado para montar el código fuente en el contenedor y ejecutar uvicorn en modo `--reload`.

Para levantar el entorno de desarrollo:

```bash
# Desde la raíz del proyecto
docker compose -f docker-compose.dev.yml up -d
```

Parar y eliminar contenedores:

```bash
docker compose -f docker-compose.dev.yml down
```

Accede a la API en `http://localhost:8080`, en desarrollo uvicorn estará en modo `--reload` y reflejará los cambios del código montado.

## Uso — Producción

El `docker-compose.prod.yml` está pensado para producción: no activa `--reload`.

Para levantar en producción:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Uso con VS Code Dev Containers

Puedes abrir este proyecto directamente en el contenedor de desarrollo usando la extensión *Dev Containers* de VS Code.

Pasos para conectar con DevContainer en VS Code:

1. Instala la extensión "Dev Containers" en VS Code.
2. Abre la carpeta del proyecto en VS Code.
3. Pulsa F1 y selecciona "Dev Containers: Reopen in Container".
4. VS Code usará `docker-compose.dev.yml` y construirá el servicio definido. El contenedor de desarrollo se abrirá y podrás depurar dentro de él.

---
