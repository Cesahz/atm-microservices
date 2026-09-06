# 📡 Endpoints — ATM System

Todos los endpoints de `account_service` requieren header:
```
Authorization: Bearer <JWT>
```
Los endpoints de `logs_service` requieren:
```
Authorization: Token <TOKEN>
```

---

## auth_service — `localhost:5001`

### `POST /login`
```json
{ "username": "Cesar Espinola", "pin": "2701" }
```
| Status | Respuesta |
|---|---|
| `200` | `{ "token": "<JWT>" }` |
| `400` | `{ "error": "Faltan credenciales" }` |
| `401` | `{ "error": "Credenciales invalidas" }` |

---

## account_service — `localhost:5002`

### `POST /retiro`
```json
{ "monto": 500000 }
```
| Status | Respuesta |
|---|---|
| `200` | `{ "mensaje": "Retiro exitoso", "monto_retirado": 500000, "nuevo_saldo": 4500000 }` |
| `400` | `{ "error": "Especifique el monto" }` |
| `400` | `{ "error": "Fondos insuficientes" }` |
| `400` | `{ "error": "Cuenta no encontrada" }` |
| `401` | `{ "error": "No autorizado. Token invalido" }` |

### `POST /transferir`
```json
{ "receptor_id": 2, "monto": 100000 }
```
| Status | Respuesta |
|---|---|
| `200` | `{ "mensaje": "Transferencia exitosa", "monto": 100000 }` |
| `400` | `{ "error": "Fondos insuficientes" }` |
| `401` | `{ "error": "No autorizado" }` |

---

## logs_service — `localhost:5000`

### `POST /logs`
Token requerido: `TOKEN-AUTH-002` / `TOKEN-PAYMENTS-003` / `TOKEN-ADMIN-005`
```json
{ "service": "atm-auth-service", "severity": "INFO", "message": "...", "timestamp": "2025-01-01T00:00:00Z" }
```
| Status | Respuesta |
|---|---|
| `201` | `{ "status": "logs guardados" }` |
| `401` | `{ "error": "No autorizado" }` |
