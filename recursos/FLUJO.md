# 🔄 Flujo del Programa — ATM System

## Diagrama

```
main.py
  │
  ├─ 1. POST /login ──────────────► auth_service
  │                                      │ valida user+PIN en db_auth
  │                                      │ genera JWT (expira 15 min)
  │                                      ▼
  │                                 logs_service ◄── log de login
  │
  │◄──── recibe JWT ────────────────────┘
  │
  ├─ 2. POST /retiro ─────────────► account_service
  │      (Bearer JWT)                    │ valida JWT
  │                                      │ descuenta saldo en db_account
  │                                      ▼
  │                                 logs_service ◄── log de retiro
  │
  └─ 3. POST /transferir ─────────► account_service
         (Bearer JWT)                    │ valida JWT
                                         │ mueve saldo entre cuentas en db_account
                                         ▼
                                    logs_service ◄── log de transferencia
```

---

## Paso a paso

**1. Autenticación**
`main.py` solicita usuario y PIN, los envía a `auth_service`. Si son válidos, recibe un JWT con el `user_id` embebido.

**2. Operación**
El usuario elige retiro o transferencia. `main.py` envía la petición a `account_service` con el JWT en el header. El servicio decodifica el token para identificar al usuario y ejecuta la operación sobre su cuenta.

**3. Logging**
Cada acción relevante (login exitoso, login fallido, retiro, transferencia) es reportada en segundo plano a `logs_service`, que la persiste en `db_logs`. Si el servicio de logs no responde, la operación continúa igual.

---

## Seguridad

| Mecanismo | Dónde aplica |
|---|---|
| JWT firmado con `SECRET_KEY` | Entre `main.py` y `account_service` |
| Token estático por servicio | Entre microservicios y `logs_service` |
| `FOR UPDATE` en SQL | Evita condiciones de carrera en retiros y transferencias simultáneas |
