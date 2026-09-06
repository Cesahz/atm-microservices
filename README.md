# 🏧 ATM System — The Huddle 7 (Remastered Edition)

Sistema transaccional distribuido de simulación de Cajero Automático (ATM) construido sobre una arquitectura de **microservicios desacoplados**, garantizando consistencia transaccional, tolerancia a fallos, auditoría centralizada y alta concurrencia.

---

## 1. Descripción Ejecutiva y Alcance Técnico

El sistema modela las operaciones críticas de una red de cajeros automáticos en un ecosistema financiero moderno. Resuelve la necesidad de procesar transacciones concurrentes con cero discrepancias contables, garantizando la seguridad en la capa de autenticación y una trazabilidad auditable en tiempo real.

### Capacidades Principales
- **Autenticación Criptográfica:** Emisión y validación de tokens JWT (`HS256`) con derivación de claves mediante PBKDF2-HMAC-SHA256 (100.000 iteraciones con sal aleatoria) para salvaguardar credenciales.
- **Consistencia Financiera & Precisión Decimal:** Eliminación de errores de redondeo de punto flotante mediante aritmética `Decimal` exacta y almacenamiento transaccional en PostgreSQL (`NUMERIC`).
- **Prevención de Condiciones de Carrera y Deadlocks:** Bloqueo pesimista determinista (`ORDER BY user_id FOR UPDATE`) que previene interbloqueos en transferencias cruzadas simultáneas.
- **Trazabilidad y Observabilidad Centralizada:** Receptor de telemetría y logs con tokenización estática por servicio, soporte de inserción en lote y endpoints analíticos agregados.
- **Cliente CLI Resiliente:** Interfaz de usuario interactiva con validación estricta de entradas y manejo defensivo de fallos de red.

---

## 2. Arquitectura y Flujo del Sistema

El sistema implementa el principio de responsabilidad única (*Single Responsibility Principle*) segregando identidad, procesamiento contable y auditoría en contenedores y esquemas de base de datos independientes.

```mermaid
flowchart TD
    CLI(["Terminal / Cliente CLI (main.py)"])

    subgraph Perímetro de Seguridad y Servicios
        AUTH["auth_service (:5001)<br/>• Validación de credenciales<br/>• Hash PBKDF2<br/>• Emisión JWT"]
        ACCOUNT["account_service (:5002)<br/>• Retiros y transferencias<br/>• Bloqueo pesimista<br/>• Aritmética Decimal"]
        LOGS["logs_service (:5000)<br/>• Centralizador de auditoría<br/>• Filtros y métricas /stats"]
    end

    subgraph Capa de Persistencia (PostgreSQL)
        DB_AUTH[("db_auth (:5433)<br/>auth_db")]
        DB_OPERADOR[("db_operador (:5434)<br/>operador_db")]
        DB_LOGS[("db_logs (:5435)<br/>logs_db")]
    end

    CLI -- "1. POST /login (username, pin)" --> AUTH
    AUTH -- "Verifica hash" --> DB_AUTH
    AUTH -. "Log login (TOKEN-AUTH-002)" .-> LOGS
    AUTH -- "Devuelve JWT (exp: 15m)" --> CLI

    CLI -- "2. POST /retiro o /transferir (Bearer JWT)" --> ACCOUNT
    ACCOUNT -- "Verifica JWT & ejecuta transacción" --> DB_OPERADOR
    ACCOUNT -. "Log transacción (TOKEN-PAYMENTS-003)" .-> LOGS
    ACCOUNT -- "Respuesta de balance" --> CLI

    LOGS -- "Persistencia en lote" --> DB_LOGS
```

### Flujo Operativo Paso a Paso
1. **Autenticación:** El cliente envía `POST /login` con credenciales de usuario. `auth_service` valida el hash contra `db_auth`, registra el evento en `logs_service` y devuelve un JWT firmado con expiración a 15 minutos.
2. **Inyección de Identidad:** El cliente adjunta el token en la cabecera HTTP `Authorization: Bearer <token>` para todas las operaciones posteriores.
3. **Ejecución Financiera:** `account_service` valida la firma del token, extrae el identificador del usuario (`user_id`), y ejecuta el débito o transferencia intercuentas asegurando la atomicidad ACID.
4. **Auditoría Silenciosa:** Cada servicio notifica sus eventos de negocio a `logs_service` de manera asíncrona y no bloqueante; una eventual caída del servicio de auditoría no interrumpe la operatoria bancaria.

---

## 3. Estructura del Repositorio

```
TheHuddle-7/
├── .env.ejemplo                  # Plantilla estandarizada de variables de configuración
├── .gitignore                    # Reglas de exclusión para bytecode, entornos y temporales
├── Dockerfile                    # Definición base unificada de imagen Docker
├── docker-compose.yml            # Orquestación de los 3 microservicios y 3 bases PostgreSQL
├── pytest.ini                    # Configuración central de ejecución para pytest
├── requirements.txt              # Dependencias fijadas del ecosistema completo
├── main.py                       # Cliente CLI interactivo refactorizado
├── tokens.py                     # Mapeo canónico tipado de tokens de auditoría
├── auth.py                       # Punto de entrada raíz para auth_service
├── operador.py                   # Punto de entrada raíz para account_service
├── server.py                     # Punto de entrada raíz para logs_service
├── test.http                     # Colección HTTP para pruebas manuales de endpoints
├── services/
│   ├── __init__.py
│   ├── auth_service/
│   │   ├── __init__.py
│   │   ├── auth.py               # API Flask (endpoints /login, /health)
│   │   ├── config.py             # Carga y validación de variables de entorno
│   │   ├── database.py           # Capa de datos con conexión resiliente y seeding
│   │   ├── security.py           # Utilidades criptográficas (PBKDF2 y PyJWT)
│   │   ├── Dockerfile            # Configuración de contenedor para auth_service
│   │   └── requirements.txt      # Dependencias específicas de auth_service
│   ├── account_service/
│   │   ├── __init__.py
│   │   ├── account.py            # API Flask (endpoints /saldo, /retiro, /transferir)
│   │   ├── config.py             # Configuración desacoplada del operador contable
│   │   ├── database.py           # Transacciones ACID, bloqueo canónico y Decimal
│   │   ├── Dockerfile            # Configuración de contenedor para account_service
│   │   └── requirements.txt      # Dependencias específicas de account_service
│   └── logs_service/
│       ├── __init__.py
│       ├── app.py                # API Flask (endpoints POST /logs, GET /logs, /stats)
│       ├── config.py             # Configuración del servicio central de logs
│       ├── database.py           # Inserción en lote, filtros SQL parametrizados y agregaciones
│       ├── tokens.py             # Validaciones de autorización de servicios emisores
│       ├── Dockerfile            # Configuración de contenedor para logs_service
│       └── requirements.txt      # Dependencias específicas de logs_service
└── tests/
    ├── conftest.py               # Fixtures compartidos, bases SQLite aisladas y clientes
    ├── test_auth_service.py      # Pruebas unitarias de autenticación y seguridad
    ├── test_account_service.py   # Pruebas unitarias de saldos, retiros y transferencias
    ├── test_logs_service.py      # Pruebas unitarias de ingesta, filtros y agregaciones
    └── test_integration_flow.py  # Prueba end-to-end del ciclo de vida del cajero
```

---

## 4. Decisiones de Diseño y Optimizaciones Técnicas

### 4.1 Eliminación de Deadlocks en Transferencias Concurrentes
- **Problema Previo:** Bloquear únicamente al emisor mediante `SELECT ... FOR UPDATE` generaba bloqueos cruzados si el Usuario A transfería al Usuario B mientras el Usuario B transfería al Usuario A. Además, si la cuenta de destino no existía, el saldo se debitaba al emisor y se perdía sin error reportado.
- **Solución Implementada:** 
  1. Se implementó un ordenamiento canónico determinista: `ORDER BY user_id FOR UPDATE` donde se bloquean ambas cuentas en orden ascendente (`min(id_emisor, id_receptor)` y luego `max(id_emisor, id_receptor)`).
  2. Se valida formalmente que ambas cuentas coexistan en la base antes de debitar un solo centavo.
  3. Se prohíbe la autotransferencia (`emisor_id == receptor_id`).

### 4.2 Mitigación de Vulnerabilidades y Almacenamiento Seguro de PINs
- **Problema Previo:** Los códigos PIN de los clientes estaban almacenados en texto plano en la base de datos (`'2701'`, `'1111'`, `'0000'`).
- **Solución Implementada:** Implementación de PBKDF2-HMAC-SHA256 con 100.000 iteraciones y sal aleatoria por usuario (`secrets.token_hex(16)`). La verificación se realiza en tiempo constante (`hmac.compare_digest`) para mitigar ataques de canal lateral basados en temporización (*timing attacks*).

### 4.3 Integridad Monetaria con Aritmética Decimal
- **Problema Previo:** Uso de números de punto flotante (`float`) de Python, propensos a pérdida de precisión binaria (IEEE 754).
- **Solución Implementada:** Uso estricto de la clase `Decimal` para todas las operaciones aritméticas de cálculo y validación de saldo. Validación estricta que rechaza montos menores o iguales a cero (`monto <= 0`), evitando inyecciones de saldo negativo.

### 4.4 Resiliencia de Arranque y Conectividad
- **Problema Previo:** En entornos Dockerizados, `depends_on` no garantiza que el socket de PostgreSQL esté listo para aceptar conexiones, provocando fallos en la inicialización al arrancar los contenedores.
- **Solución Implementada:**
  1. Adición de `healthcheck` oficial con `pg_isready` en `docker-compose.yml`.
  2. Implementación de reconexión con reintento y retroceso exponencial (*exponential backoff*) en cada capa de base de datos.
  3. Capa de persistencia desacoplada que soporta PostgreSQL en producción y SQLite en memoria/archivo para ejecución instantánea de suites de pruebas automáticas sin requerir contenedores activos.

### 4.5 Estandarización de Patrones de Arquitectura
- **Application Factory:** Cada microservicio expone `create_app(test_config=None)`, permitiendo inyección de dependencias y aislamiento hermético en pruebas unitarias.
- **Tipado Estricto (PEP 484):** Firmas de funciones y métodos anotadas con `typing` estricto (`Optional`, `Tuple`, `Dict`, `Union`, `Decimal`), minimizando errores en tiempo de ejecución.

---

## 5. Requisitos Previos y Entorno

- **Runtime:** Python 3.10 o superior (validado en Python 3.10, 3.11, 3.12 y 3.13).
- **Orquestador de Contenedores (Opcional para modo completo):** Docker Engine 20.10+ y Docker Compose v2+.
- **Dependencias Principales:**
  - `Flask >= 2.3.2` (Framework web ligero y desacoplado)
  - `psycopg2-binary >= 2.9.6` (Adaptador de base de datos PostgreSQL)
  - `PyJWT >= 2.8.0` (Generación y verificación criptográfica de JWT)
  - `requests >= 2.31.0` (Cliente HTTP para auditoría y CLI)
  - `python-dotenv >= 1.0.0` (Carga de variables de entorno)
  - `pytest >= 7.4.0` y `pytest-cov >= 4.1.0` (Suite de testing y análisis de cobertura)

---

## 6. Guía de Instalación y Ejecución Local

### Opción A: Despliegue Completo con Docker Compose (Recomendado para Producción)

1. **Configuración de Variables de Entorno:**
   ```bash
   cp .env.ejemplo .env
   ```

2. **Compilación y Arranque de Microservicios:**
   ```bash
   docker compose up --build
   ```
   > Los contenedores inicializarán automáticamente sus tablas, índices y datos iniciales una vez los motores de PostgreSQL alcancen el estado saludable (`healthy`).

3. **Ejecución del Cliente CLI:**
   En otra terminal:
   ```bash
   python main.py
   ```

---

### Opción B: Ejecución Local Nativa (Desarrollo y Testing sin Docker)

1. **Creación y Activación del Entorno Virtual:**
   - En Linux/macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - En Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

2. **Instalación de Dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecución de los Servicios de Forma Individual:**
   Cada microservicio puede iniciarse directamente utilizando su punto de entrada modular:
   ```bash
   # Terminal 1: Servicio de Logs (Puerto 5000)
   python server.py

   # Terminal 2: Servicio de Autenticación (Puerto 5001)
   python auth.py

   # Terminal 3: Servicio de Cuentas (Puerto 5002)
   python operador.py

   # Terminal 4: Cliente CLI
   python main.py
   ```

---

## 7. Catálogo de Cuentas de Prueba Preconfiguradas

| ID | Titular de la Cuenta | PIN Inicial | Saldo Inicial |
|:--:|:---------------------|:-----------:|:-------------:|
| `1` | Cesar Espinola       | `2701`      | 5.000.000 Gs. |
| `2` | Jose Toledo          | `1111`      | 7.000.000 Gs. |
| `3` | Penguin Academy      | `0000`      | 999.999.999 Gs. |

---

## 8. Batería de Pruebas Automatizadas

El proyecto cuenta con una cobertura integral de pruebas unitarias, de límites y de integración end-to-end implementadas con `pytest`.

### Ejecución de Pruebas

Para ejecutar la suite completa con reporte detallado:
```bash
pytest
```

Para ejecutar con análisis de cobertura de código:
```bash
pytest --cov=services --cov-report=term-missing
```

### Resumen de Escenarios Validados (25/25 Casos Pasados)
- **`test_auth_service.py`:**
  - Login exitoso para todos los usuarios semilla.
  - Rechazo de credenciales inválidas (PIN incorrecto, usuario inexistente).
  - Manejo de entradas malformadas y campos ausentes (HTTP 400).
  - Almacenamiento no reversible de PINs mediante PBKDF2.
  - Firma, tiempo de vida y expiración de tokens JWT.
- **`test_account_service.py`:**
  - Retiro válido y decremento exacto del saldo.
  - Prevención de sobregiro por fondos insuficientes.
  - Bloqueo y rechazo estricto de montos negativos, cero y caracteres no numéricos.
  - Exigencia de autorización JWT válida (HTTP 401).
  - Transferencias válidas entre cuentas con débito y crédito simétrico.
  - Rechazo de transferencias hacia la misma cuenta.
  - Rechazo de transferencias hacia cuentas inexistentes sin alteración de balance.
- **`test_logs_service.py`:**
  - Recepción individual y masiva en lote (*batch*).
  - Validación de tokens estáticos autorizados (`TOKEN-AUTH-002`, `TOKEN-PAYMENTS-003`, `TOKEN-ADMIN-005`).
  - Validación de severidades permitidas (`INFO`, `DEBUG`, `WARN`, `ERROR`, `FATAL`).
  - Filtrado dinámico de logs por servicio y nivel.
  - Cálculo agregado de métricas en `/stats`.
- **`test_integration_flow.py`:**
  - Simulación completa de interacción: Login -> Consulta de saldo -> Retiro -> Transferencia -> Login destinatario -> Verificación de nuevo saldo -> Auditoría de registros.
