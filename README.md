# Control de Cargas GYM

PWA móvil para llevar el control de las cargas que levanta un equipo en el gimnasio.
El entrenador da de alta las sesiones desde el móvil y cada jugador registra sus kg
serie a serie. Todo se puede exportar a Excel.

## Cómo funciona

**El jugador** abre la web, toca su nombre, marca su PIN de 4 dígitos y ya ve la batería
del día. Por cada serie tiene dos steppers grandes (kg y repeticiones): cada toque guarda
solo, sin botón de "enviar". Debajo de cada ejercicio aparece lo que levantó la última vez,
para saber por dónde iba.

**El entrenador** entra con usuario y contraseña. Desde el panel crea la batería del día,
elige los ejercicios con series/reps/descanso y decide a quién va: a todo el equipo, a un
grupo (porteros, lesionados…) o a jugadores concretos. Puede duplicar una batería a otro
día con un toque, ver en tiempo real qué jugadores han registrado ya sus series y descargar
el Excel.

## Puesta en marcha

### Con Docker (recomendado)

```bash
cp .env.example .env
# Rellena SECRET_KEY (openssl rand -hex 32) y COACH_PASSWORD
docker compose up -d --build
```

La app queda en `http://localhost:8080`. En el primer arranque se crean el usuario del
entrenador (según el `.env`) y un catálogo de 12 ejercicios base para no empezar en blanco.

Los datos viven en el volumen `cargas-data`. Para respaldarlos:

```bash
docker compose cp backend:/data/cargas.db ./copia-cargas.db
```

### En local, sin Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # rellena SECRET_KEY y COACH_PASSWORD
uvicorn app.main:app --reload

# Frontend, en otra terminal
cd frontend
npm install
npm run dev                   # http://localhost:5173, ya proxea /api al backend
```

La documentación interactiva de la API queda en `http://localhost:8000/docs`.

## Instalarla en el móvil

Es una PWA: al abrir la web en el móvil, "Añadir a pantalla de inicio" la deja como una app
más, a pantalla completa y sin barra del navegador.

Si un jugador se queda sin cobertura en el gimnasio, las series que registre se guardan en
el móvil y se marcan en ámbar como "sin enviar"; en cuanto vuelve la red se suben solas.

## Stack

| Capa | Tecnología |
| --- | --- |
| Frontend | Vue 3 (Composition API), Vite, Pinia, Vue Router, Tailwind CSS, `vite-plugin-pwa` |
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, PyJWT, passlib/bcrypt |
| Base de datos | SQLite (cambiar `DATABASE_URL` basta para pasar a PostgreSQL) |
| Excel | openpyxl |
| Despliegue | Docker Compose (nginx sirve la SPA y proxea `/api` al backend) |

## Estructura

```
backend/
  app/
    api/          auth, coach, player, export
    core/         configuración, seguridad (JWT + hashes), base de datos
    models/       tablas SQLAlchemy
    schemas/      esquemas Pydantic de entrada y salida
    services/     asignación de rutinas y generación del Excel
  tests/          suite de pytest
frontend/
  src/
    api/          cliente HTTP
    components/   stepper, tarjeta de ejercicio, shell de pantalla
    stores/       Pinia: sesión y entrenamiento (con cola offline)
    views/        pantallas de jugador y de entrenador
```

## Modelo de datos

- **users** — jugadores y entrenador; los jugadores guardan `pin_hash`, el entrenador `password_hash`.
- **groups** / **player_groups** — grupos de trabajo y a cuáles pertenece cada jugador.
- **exercises** — catálogo con nombre, categoría y descripción.
- **routines** — la batería de un día, con sus notas.
- **routine_exercises** — cada ejercicio dentro de una batería, con series, reps objetivo y descanso.
- **routine_assignments** — a quién va dirigida: `all`, `group` o `player`.
- **set_logs** — la carga de una serie concreta: kg, reps y jugador. Es única por
  jugador + ejercicio + número de serie, así que corregir una serie la sobrescribe en vez
  de duplicarla.

## API

| Método | Ruta | Quién | Qué hace |
| --- | --- | --- | --- |
| `GET` | `/api/auth/players` | público | Lista de nombres para el selector de login (solo `id` y `name`) |
| `POST` | `/api/auth/login/player` | público | Valida jugador + PIN y devuelve el JWT |
| `POST` | `/api/auth/login/coach` | público | Valida usuario + contraseña y devuelve el JWT |
| `GET` | `/api/auth/me` | autenticado | Datos del usuario de la sesión |
| `GET` | `/api/routines/today` | jugador | Batería del día que le corresponde, con sus cargas ya registradas |
| `GET` | `/api/routines/mine` | jugador | Últimas sesiones asignadas |
| `POST` | `/api/logs` | jugador | Guarda o corrige la carga de una serie |
| `GET`/`POST`/`PATCH`/`DELETE` | `/api/coach/players`, `/groups`, `/exercises` | entrenador | Gestión de plantilla, grupos y catálogo |
| `GET`/`POST`/`PUT`/`DELETE` | `/api/coach/routines` | entrenador | Baterías |
| `POST` | `/api/coach/routines/{id}/duplicate` | entrenador | Copia una batería a otra fecha |
| `GET` | `/api/coach/routines/{id}/progress` | entrenador | Series registradas por cada jugador |
| `GET` | `/api/export/excel` | entrenador | Descarga el `.xlsx` filtrado por fechas y jugador |

## El Excel

Trae dos hojas:

- **Cargas** — una fila por serie: fecha, batería, jugador, ejercicio, categoría, número de
  serie, kg, reps hechas y reps objetivo. Con filtros y primera fila fija.
- **Resumen** — por jugador y ejercicio: número de series, kg máximo, kg medio y volumen
  total (kg × reps).

Acepta filtros `date_from`, `date_to` y `player_id`; sin filtros exporta todo el histórico.

## Tests

```bash
cd backend && python -m pytest
```

Cubren el login de ambos roles, que un jugador no pueda entrar al panel ni registrar cargas
en una batería que no es suya, que las asignaciones por grupo funcionen, el historial de la
sesión anterior, la duplicación de baterías y la exportación a Excel.

## Seguridad

- Los PIN y las contraseñas se guardan hasheados con bcrypt, nunca en claro.
- La lista pública de jugadores del login solo devuelve `id` y `name`.
- Cada endpoint del panel comprueba el rol: un JWT de jugador recibe un 403.
- Un jugador solo puede escribir cargas en baterías que tenga asignadas.
- `SECRET_KEY` y `COACH_PASSWORD` son obligatorias en `docker compose`: sin ellas no arranca.

Cambia la contraseña del entrenador tras el primer acceso y, si publicas la app fuera de la
red local, sírvela por HTTPS.
