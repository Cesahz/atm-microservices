# 🏧 ATM System — The Huddle 7

Simulación de un cajero automático construida sobre una arquitectura de **3 microservicios** independientes, cada uno con su propia base de datos PostgreSQL, orquestados con Docker Compose.

---

## 📐 Arquitectura General

```
main.py (cliente CLI)
    │
    ├──► auth_service   :5001  →  db_auth      (PostgreSQL :5433)
    │        Autentica al usuario, emite JWT
    │
    ├──► account_service :5002  →  db_account   (PostgreSQL :5434)
    │        Procesa retiros y transferencias
    │
    └──► logs_service   :5000  →  db_logs      (PostgreSQL :5435)
             Recibe y almacena logs de los otros dos servicios
```

---

## 🔄 Flujo Completo de una Operación

```
1. El usuario ejecuta main.py e ingresa usuario + PIN.

2. main.py  ──POST /login──►  auth_service
   auth_service valida las credenciales contra db_auth.
   Si son correctas, genera un JWT firmado (expira en 15 min) y lo devuelve.
   auth_service envía un log a logs_service.

3. main.py almacena el token y lo adjunta como header
   "Authorization: Bearer <token>" en cada operación.

4. El usuario elige Retirar o Transferir.

5. main.py  ──POST /retiro o /transferir──►  account_service
   account_service valida el JWT (misma SECRET_KEY).
   Ejecuta la operación sobre db_account.
   account_service envía un log a logs_service.

6. logs_service recibe los logs (autenticados con token estático)
   y los persiste en db_logs.
```

---

## 🧩 Microservicios

### 1. `logs_service` — Puerto 5000

Receptor centralizado de logs. Todos los demás servicios le reportan eventos. Autentica las peticiones con tokens estáticos definidos en `tokens.py`.

**Tokens válidos:**

| Token | Servicio autorizado |
|---|---|
| `TOKEN-AUTH-002` | auth_service |
| `TOKEN-PAYMENTS-003` | account_service |
| `TOKEN-ADMIN-005` | Admin (acceso manual) |

---

### 2. `auth_service` — Puerto 5001

Guardián de identidad. Verifica usuario + PIN contra la base de datos y emite un JWT firmado con `SECRET_KEY`. El token incluye el `user_id` y expira en 15 minutos.

**Usuarios precargados:**

| ID | Username | PIN |
|---|---|---|
| 1 | Cesar Espinola | 2701 |
| 2 | Jose Toledo | 1111 |
| 3 | Penguin Academy | 0000 |

---

### 3. `account_service` — Puerto 5002

Operador financiero. Valida el JWT en cada request antes de ejecutar cualquier operación. Usa `FOR UPDATE` en las consultas SQL para evitar condiciones de carrera en operaciones concurrentes.

**Saldos iniciales:**

| user_id | Saldo (Gs) |
|---|---|
| 1 | 5.000.000 |
| 2 | 7.000.000 |
| 3 | 999.999.999 |

---

## 📡 Endpoints

### `auth_service` — `http://localhost:5001`

#### `POST /login`

Autentica al usuario y devuelve un token JWT.

**Headers:** ninguno requerido.

**Body (JSON):**
```json
{
  "username": "Cesar Espinola",
  "pin": "2701"
}
```

**Respuestas:**

| Status | Descripción | Body ejemplo |
|---|---|---|
| `200 OK` | Login exitoso | `{ "token": "<JWT>" }` |
| `400 Bad Request` | Faltan campos | `{ "error": "Faltan credenciales" }` |
| `401 Unauthorized` | Credenciales inválidas | `{ "error": "Credenciales invalidas" }` |

---

### `account_service` — `http://localhost:5002`

Todos los endpoints requieren el JWT en el header:
```
Authorization: Bearer <token>
```

#### `POST /retiro`

Descuenta el monto indicado del saldo del usuario autenticado.

**Body (JSON):**
```json
{
  "monto": 500000
}
```

**Respuestas:**

| Status | Descripción | Body ejemplo |
|---|---|---|
| `200 OK` | Retiro exitoso | `{ "mensaje": "Retiro exitoso", "monto_retirado": 500000, "nuevo_saldo": 4500000 }` |
| `400 Bad Request` | Monto no especificado | `{ "error": "Especifique el monto" }` |
| `400 Bad Request` | Saldo insuficiente | `{ "error": "Fondos insuficientes" }` |
| `400 Bad Request` | Cuenta no existe | `{ "error": "Cuenta no encontrada" }` |
| `401 Unauthorized` | Token inválido o expirado | `{ "error": "No autorizado. Token invalido" }` |

---

#### `POST /transferir`

Mueve un monto desde la cuenta del usuario autenticado hacia otra cuenta.

**Body (JSON):**
```json
{
  "receptor_id": 2,
  "monto": 100000
}
```

**Respuestas:**

| Status | Descripción | Body ejemplo |
|---|---|---|
| `200 OK` | Transferencia exitosa | `{ "mensaje": "Transferencia exitosa", "monto": 100000 }` |
| `400 Bad Request` | Saldo insuficiente | `{ "error": "Fondos insuficientes" }` |
| `401 Unauthorized` | Token inválido o expirado | `{ "error": "No autorizado" }` |

---

### `logs_service` — `http://localhost:5000`

#### `POST /logs`

Recibe uno o varios logs y los persiste en la base de datos.

**Headers:**
```
Authorization: Token TOKEN-AUTH-002
```

**Body (JSON) — objeto único o lista:**
```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "service": "atm-auth-service",
  "severity": "INFO",
  "message": "Login exitoso para usuario: Cesar Espinola"
}
```

**Severidades válidas:** `INFO`, `WARN`, `ERROR`

**Respuestas:**

| Status | Descripción | Body ejemplo |
|---|---|---|
| `201 Created` | Logs guardados | `{ "status": "logs guardados" }` |
| `401 Unauthorized` | Token inválido | `{ "error": "No autorizado" }` |

---

## 🚀 Cómo levantar el sistema

### Prerrequisitos
- Docker y Docker Compose instalados.

### Pasos

```bash
# 1. Clonar el repositorio y navegar a la raíz
cd atm-system

# 2. Renombrar el archivo de entorno
cp _env .env

# 3. Levantar todos los servicios
docker compose up --build

# 4. En otra terminal, ejecutar el cliente
python main.py
```

> Los servicios inicializan sus bases de datos automáticamente al arrancar.

---

## ⚙️ Variables de Entorno (`.env`)

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DB_USER` | Usuario de PostgreSQL | `admin` |
| `DB_PASSWORD` | Contraseña de PostgreSQL | `password` |
| `JWT_SECRET` | Clave para firmar/verificar JWTs | `secreto_del_pinguino_aislado` |

> ⚠️ En producción, reemplazar todos estos valores por credenciales seguras.

---

## 🐳 Documentación Docker

### Dockerfile (común a los 3 servicios)

```dockerfile
FROM python:3.9-slim
```
Define la imagen base. `python:3.9-slim` es una imagen oficial de Python reducida en tamaño, sin herramientas de compilación innecesarias.

```dockerfile
WORKDIR /app
```
Establece el directorio de trabajo dentro del contenedor. Todos los comandos posteriores se ejecutan desde `/app`.

```dockerfile
COPY requirements.txt .
```
Copia solo el archivo de dependencias primero. Esto aprovecha la **caché de capas de Docker**: si `requirements.txt` no cambia, Docker no reinstala los paquetes en cada build.

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```
Instala las dependencias de Python. `--no-cache-dir` evita guardar caché de pip dentro de la imagen, reduciendo su tamaño final.

```dockerfile
COPY . .
```
Copia el resto del código fuente al directorio de trabajo del contenedor.

```dockerfile
CMD ["python", "-u", "app.py"]
```
Comando que se ejecuta al iniciar el contenedor. `-u` deshabilita el buffering de salida, lo que permite ver los `print()` en tiempo real en los logs de Docker.

---

### docker-compose.yml

```yaml
version: '3.8'
```
Especifica la versión del esquema de Docker Compose. La versión `3.8` es compatible con Docker Engine 19.03+ y soporta todas las funcionalidades modernas.

---

#### Definición de un servicio de base de datos

```yaml
db_logs:
  image: postgres:15
  environment:
    POSTGRES_USER: ${DB_USER}
    POSTGRES_PASSWORD: ${DB_PASSWORD}
    POSTGRES_DB: logs_db
  ports:
    - "5435:5432"
```

| Directiva | Descripción |
|---|---|
| `image` | Usa la imagen oficial de PostgreSQL versión 15 directamente desde Docker Hub, sin necesidad de Dockerfile. |
| `environment` | Variables de entorno inyectadas al contenedor. `${DB_USER}` lee el valor desde el archivo `.env`. |
| `ports` | Mapeo `HOST:CONTENEDOR`. El puerto `5432` interno se expone como `5435` en la máquina local, evitando conflictos entre las 3 bases de datos. |

---

#### Definición de un microservicio

```yaml
logs_service:
  build: ./services/logs_service
  ports:
    - "5005:5000"
  environment:
    - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db_logs:5432/logs_db
  depends_on:
    - db_logs
```

| Directiva | Descripción |
|---|---|
| `build` | Ruta al directorio que contiene el `Dockerfile`. Docker construye la imagen localmente. |
| `ports` | Expone el puerto `5000` interno como `5000` (o `5005` en el caso de logs) en el host. |
| `environment` | La `DATABASE_URL` usa el nombre del servicio (`db_logs`) como hostname. Docker Compose crea una red interna donde los contenedores se resuelven por nombre de servicio. |
| `depends_on` | Garantiza que `db_logs` inicie antes que `logs_service`. No espera a que la DB esté *lista*, solo a que el contenedor haya *arrancado*. |

---

#### Red interna

Docker Compose crea automáticamente una red virtual privada para todos los servicios del archivo. Dentro de esa red, cada servicio es accesible por su nombre (por ejemplo, `http://logs_service:5000`). Desde el host, se accede por `localhost` en el puerto mapeado.

```
Host (localhost)          Red interna Docker
─────────────────         ──────────────────────────────
:5001  ──────────────►    auth_service:5001
:5002  ──────────────►    account_service:5002
:5000  ──────────────►    logs_service:5000
:5433  ──────────────►    db_auth:5432
:5434  ──────────────►    db_account:5432
:5435  ──────────────►    db_logs:5432
```
