# ChatBot WhatsApp — Sistema de Mensajería Automatizada

Sistema de mensajería WhatsApp sin API oficial, diseñado para tres casos de uso reales: autenticación OTP, recordatorios de taller y campañas de marketing con control de velocidad. Construido con una arquitectura de dos microservicios desacoplados: un cerebro en Python/Flask y un mensajero en Node.js/Baileys.

---

## Índice

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Estructura de Carpetas](#2-estructura-de-carpetas)
3. [Guía de Instalación Local](#3-guía-de-instalación-local)
4. [Referencia de Endpoints](#4-referencia-de-endpoints)
5. [Guía de Prompting para IA](#5-guía-de-prompting-para-ia)

---

## 1. Arquitectura del Sistema

### Diagrama de flujo

```
Tu Aplicación Web
        │
        │ HTTP REST
        ▼
┌───────────────────────────────┐
│   BACKEND — Python / Flask    │  :5000
│                               │
│  • Blueprints (rutas REST)    │
│  • Peewee ORM → MariaDB       │
│  • APScheduler (jobs 1 min)   │
│  • Lógica OTP / recordatorios │
└───────────┬───────────────────┘
            │ HTTP POST interno
            │ Header: x-api-key
            ▼
┌───────────────────────────────┐
│  MICROSERVICIO — Node.js      │  :3000
│                               │
│  • Express (endpoints REST)   │
│  • Baileys (protocolo WA Web) │
│  • Cola de marketing async    │
└───────────┬───────────────────┘
            │ WebSocket cifrado
            │ (protocolo Signal)
            ▼
      WhatsApp Web / Móvil
```

### Decisiones de diseño

**¿Por qué dos servicios separados?**

Flask y Node.js hacen cosas distintas y cada uno es el mejor en su dominio. Flask maneja lógica de negocio, base de datos y scheduler con la madurez del ecosistema Python. Node.js maneja la conexión WebSocket persistente con WhatsApp con su modelo de I/O no bloqueante, ideal para esperar eventos de red. Desacoplarlos permite reiniciar uno sin afectar al otro, y escalarlos de forma independiente.

**¿Cómo se comunican Flask y Node.js?**

Flask actúa como cliente HTTP del microservicio Node.js. Cada vez que necesita enviar un mensaje, hace un `POST` al endpoint `/enviar` o `/enviar-campana` de Node.js, incluyendo el header `x-api-key` con una clave secreta compartida. Node.js valida esa clave antes de procesar cualquier petición, bloqueando accesos externos. El puerto 3000 nunca debe exponerse a internet, sólo Flask lo conoce.

**¿Qué es Peewee y por qué no SQLAlchemy?**

Peewee es un ORM Python minimalista. Define los modelos de la base de datos como clases Python, traduce operaciones a SQL, gestiona conexiones y permite hacer consultas expresivas sin escribir SQL crudo. Se eligió sobre SQLAlchemy por su simplicidad: mismo poder para un proyecto de esta escala, con una API mucho más directa. La gestión de conexiones es manual (`connection_context()`) para ser seguros con los hilos de APScheduler.

**¿Por qué Baileys y no la API oficial de Meta?**

La API oficial de WhatsApp Business de Meta requiere aprobación empresarial, tiene costos por conversación y restricciones de plantillas. Baileys reimplementa el protocolo de WhatsApp Web (basado en el protocolo Signal de cifrado extremo a extremo) directamente en Node.js. Permite vincular una cuenta normal de WhatsApp escaneando un QR, exactamente igual que WhatsApp Web en el navegador. Las credenciales de sesión se guardan en `auth_info/` y persisten entre reinicios.

**¿Cómo funciona la cola de marketing sin bloquear Node.js?**

Node.js es monohilo. Un `sleep()` bloqueante detendría Express completamente. La cola usa `async/await` con `setTimeout` envuelto en una `Promise`: cuando se llama `await esperar(30000)`, la función se suspende pero el hilo devuelve el control al Event Loop, que sigue atendiendo peticiones HTTP. La pausa es de 15 a 45 segundos aleatoria para imitar comportamiento humano y evitar detección como spam.

---

## 2. Estructura de Carpetas

```
ChatBotWhatsapp/
├── .gitignore
├── README.md
├── estructura_base_datos.sql        ← Schema SQL sin datos reales
│
├── backend/                         ← Servicio Python/Flask
│   ├── .env.example                 ← Plantilla de variables (copiar a .env)
│   ├── requirements.txt
│   ├── config.py                    ← Carga centralizada de variables de entorno
│   ├── models.py                    ← Modelos Peewee: Usuario, ValidacionLogin, MantenimientoTaller
│   ├── scheduler.py                 ← APScheduler: jobs de recordatorios 24h y 1h
│   ├── app.py                       ← Factory Flask: registra blueprints y arrancar scheduler
│   ├── routes/
│   │   ├── auth.py                  ← POST /auth/solicitar-otp, /auth/verificar-otp
│   │   ├── taller.py                ← CRUD /taller/citas
│   │   └── marketing.py             ← POST /marketing/campana
│   └── services/
│       ├── whatsapp.py              ← Cliente HTTP interno → Node.js
│       └── otp.py                   ← Generación y validación de códigos OTP
│
└── microservicio/                   ← Servicio Node.js/Baileys
    ├── .env.example
    ├── package.json
    └── src/
        ├── index.js                 ← Entrada: Express + arranque de Baileys
        ├── whatsapp.js              ← Singleton de conexión Baileys con reconexión automática
        ├── queue.js                 ← Cola de marketing no bloqueante con delays aleatorios
        └── routes/
            └── enviar.js            ← POST /enviar, /enviar-campana, GET /estado-cola
```

---

## 3. Guía de Instalación Local

### Requisitos previos

| Herramienta | Versión mínima | Verificar con |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| MariaDB / MySQL | 10.6+ | `mariadb --version` |
| npm | 9+ | `npm --version` |

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/DaBeMCC/ChatbotWhatsapp.git
cd ChatbotWhatsapp
```

### Paso 2 — Base de datos

El archivo `estructura_base_datos.sql` contiene **sólo la estructura** de las tablas, sin ningún dato real. Esto es intencional: protege los números de teléfono y datos personales del entorno de desarrollo original.

```bash
# Crear la base de datos y un usuario dedicado (ejecutar como root de MariaDB)
sudo mariadb -e "
CREATE DATABASE IF NOT EXISTS chatbot_whatsapp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'chatbot'@'localhost' IDENTIFIED BY 'chatbot2024';
GRANT ALL PRIVILEGES ON chatbot_whatsapp.* TO 'chatbot'@'localhost';
FLUSH PRIVILEGES;
"

# Importar la estructura
mariadb -u chatbot -pchatbot2024 chatbot_whatsapp < estructura_base_datos.sql

# Verificar que las tablas se crearon
mariadb -u chatbot -pchatbot2024 chatbot_whatsapp -e "SHOW TABLES;"
```

Deberías ver:
```
Tables_in_chatbot_whatsapp
mantenimientos_taller
usuarios
validaciones_login
```

### Paso 3 — Backend Python

```bash
cd backend

# Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env          # Edita con tus credenciales locales
```

Contenido mínimo del `.env` del backend:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=chatbot_whatsapp
DB_USER=chatbot
DB_PASSWORD=chatbot2024
WHATSAPP_SERVICE_URL=http://localhost:3000
INTERNAL_API_KEY=una-clave-secreta-larga-que-tu-elijas
OTP_EXPIRY_MINUTES=5
SECRET_KEY=otra-clave-secreta-para-flask
```

> **IMPORTANTE:** El valor de `INTERNAL_API_KEY` debe ser **idéntico** en el `.env` del backend y en el `.env` del microservicio. Es el secreto compartido que protege la comunicación interna entre los dos servicios.

Arrancar Flask:

```bash
# Dentro de backend/ con el .venv activo
python app.py
```

El scheduler de APScheduler arranca automáticamente junto con Flask y revisará las citas cada minuto.

### Paso 4 — Microservicio Node.js

```bash
cd ../microservicio

# Instalar dependencias
npm install

# Si npm pide aprobar scripts de instalación:
npm approve-scripts @whiskeysockets/baileys
npm approve-scripts protobufjs
npm install   # volver a ejecutar tras aprobar

# Configurar variables
cp .env.example .env
nano .env
```

Contenido del `.env` del microservicio:

```env
PORT=3000
INTERNAL_API_KEY=una-clave-secreta-larga-que-tu-elijas
```

Arrancar el microservicio:

```bash
npm start
```

### Paso 5 — Vincular WhatsApp

La primera vez que ejecutes `npm start`, aparecerá un código QR en la terminal:

```
[WhatsApp] Escanea el QR para vincular tu cuenta:

▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
█ ▄▄▄▄▄ █▄▀  ▄▄ ▄▀ ...
```

1. Abre WhatsApp en tu celular
2. Ve a **Menú → Dispositivos vinculados → Vincular un dispositivo**
3. Apunta la cámara al QR

Cuando veas `[WhatsApp] ✓ Conexión establecida correctamente.`, el sistema está listo.

Las credenciales se guardan en `auth_info/` (está en `.gitignore`). Los reinicios posteriores no pedirán QR.

### Paso 6 — Verificar que todo funciona

```bash
# Salud del microservicio (no requiere API key)
curl http://localhost:3000/health

# Crear un usuario de prueba en la DB
mariadb -u chatbot -pchatbot2024 chatbot_whatsapp -e \
  "INSERT INTO usuarios (telefono, nombre, activo, created_at)
   VALUES ('51999999999', 'Usuario Prueba', 1, NOW());"

# Solicitar OTP (Flask llama internamente a Node.js → WhatsApp)
curl -X POST http://localhost:5000/auth/solicitar-otp \
  -H "Content-Type: application/json" \
  -d '{"telefono": "51999999999"}'
```

---

## 4. Referencia de Endpoints

### Backend Flask — `http://localhost:5000`

| Método | Ruta | Body JSON | Descripción |
|---|---|---|---|
| `POST` | `/auth/solicitar-otp` | `{"telefono": "51912345678"}` | Genera y envía OTP por WhatsApp |
| `POST` | `/auth/verificar-otp` | `{"telefono": "...", "codigo": "123456"}` | Valida el código recibido |
| `POST` | `/taller/citas` | `{"usuario_id": 1, "descripcion": "...", "fecha_cita": "2026-12-01T10:00:00"}` | Crea cita de taller |
| `GET` | `/taller/citas/usuario/<id>` | — | Lista citas activas de un usuario |
| `DELETE` | `/taller/citas/<id>` | — | Cancela una cita |
| `POST` | `/marketing/campana` | `{"mensaje": "Hola {nombre}...", "usuarios_ids": [1, 2, 3]}` | Encola campaña con delays anti-spam |

### Microservicio Node.js — `http://localhost:3000`

> Todos excepto `/health` requieren el header `x-api-key`.

| Método | Ruta | Body JSON | Descripción |
|---|---|---|---|
| `GET` | `/health` | — | Estado del servicio |
| `POST` | `/enviar` | `{"telefono": "51912345678", "mensaje": "Texto"}` | Envío inmediato (OTP, recordatorios) |
| `POST` | `/enviar-campana` | `{"destinatarios": [{"telefono": "...", "mensaje": "..."}]}` | Encola con delays 15–45s |
| `GET` | `/estado-cola` | — | Mensajes en cola, enviados y errores |

---

## 5. Guía de Prompting para IA

Esta sección está diseñada para ser **copiada íntegra y pegada al inicio de una conversación con Claude u otra IA** cuando necesites hacer cambios profundos al proyecto. Provee el contexto arquitectónico necesario para que la IA razone correctamente sin romper el sistema.

---

### Bloque de contexto (copiar y pegar completo)

```
Actúa como un Ingeniero de Software Senior experto en Python (Flask/Peewee) y Node.js (Baileys).

## Contexto del proyecto

Tengo un sistema de mensajería WhatsApp sin API oficial compuesto por dos microservicios:

### Servicio 1 — Backend (Python, puerto 5000)
- Framework: Flask con patrón de factory (`create_app()`)
- ORM: Peewee con MySQLDatabase (autoconnect=False, gestión manual por hilo)
- Scheduler: APScheduler BackgroundScheduler, 2 jobs cada 1 minuto
- Modelos: Usuario (telefono único con código de país), ValidacionLogin (OTP 6 dígitos + expiración), MantenimientoTaller (fecha_cita, recordatorio_24h_enviado, recordatorio_1h_enviado, cancelado)
- Estructura: routes/ (Blueprints), services/ (clientes HTTP y lógica OTP), scheduler.py, models.py, config.py

### Servicio 2 — Microservicio (Node.js, puerto 3000)
- Framework: Express.js con ES Modules (type: "module" en package.json)
- WhatsApp: @whiskeysockets/baileys con makeWASocket y useMultiFileAuthState
- Cola de marketing: clase ColaMensajes con async/await + setTimeout (no bloqueante) con delays aleatorios 15–45 segundos
- Auth interna: header x-api-key validado en middleware de Express

### Comunicación entre servicios
Flask llama a Node.js via HTTP POST con el header x-api-key. Node.js NUNCA es llamado directamente por el exterior; solo Flask lo consume.

### Base de datos
MariaDB local. Tablas: usuarios, validaciones_login, mantenimientos_taller.

### Invariantes que NO deben romperse
1. La gestión de conexiones de Peewee debe usar `database.connection_context()` en los jobs del scheduler para evitar errores de hilo.
2. La autenticación entre servicios siempre va por header x-api-key.
3. La cola de marketing NUNCA debe bloquear el Event Loop de Node.js.
4. Los jobs de APScheduler NO necesitan Flask app context (usan Peewee directamente).
5. Los archivos .env, auth_info/ y node_modules/ jamás van a git.

## Mi solicitud
[ESCRIBE AQUÍ LO QUE NECESITAS]
```

---

### Ejemplos de uso del bloque de contexto

#### Ejemplo A — Migrar la base de datos de MariaDB a MongoDB

Pega el bloque de contexto y agrega al final:

```
## Mi solicitud

Quiero migrar la capa de persistencia del backend de MariaDB+Peewee a MongoDB+PyMongo.
Necesito que:
1. Me expliques qué cambia en models.py (de tablas relacionales a colecciones de documentos)
   y cómo rediseñarías el esquema para los 3 modelos actuales.
2. Me indiques si los jobs de APScheduler en scheduler.py necesitan cambiar su gestión
   de conexión (actualmente usan database.connection_context()).
3. Escribas el archivo models.py completo reemplazando Peewee por PyMongo,
   manteniendo la misma interfaz que consumen las rutas de Flask.
4. Actualices requirements.txt.
No toques el microservicio Node.js ni la cola de marketing, esa capa no cambia.
```

#### Ejemplo B — Preparar el despliegue en AWS

Pega el bloque de contexto y agrega al final:

```
## Mi solicitud

Quiero desplegar este sistema en AWS. Necesito que te enfoques exclusivamente en:
1. Qué servicio de AWS es el más adecuado para cada componente y por qué:
   - Flask backend (EC2, Elastic Beanstalk, ECS con Fargate, Lambda)
   - Node.js microservicio con Baileys (restricción importante: necesita WebSocket
     persistente y estado en disco para auth_info/)
   - Base de datos MariaDB (RDS vs EC2 self-managed)
2. Cómo manejar el secreto INTERNAL_API_KEY entre los dos servicios en AWS
   (AWS Secrets Manager, Parameter Store o variable de entorno en task definition).
3. Qué implica que Baileys necesite persistir auth_info/ en disco:
   por qué ECS Fargate sin EFS o Lambda son malas opciones para el microservicio Node.js.
4. Un diagrama ASCII de la arquitectura AWS resultante.
No escribas código todavía, primero necesito validar el diseño.
```

---

> **Nota para el equipo:** Mantén esta sección actualizada si la arquitectura cambia significativamente (nuevo servicio, cambio de ORM, nuevo proveedor de nube). Una IA con contexto desactualizado genera código que rompe invariantes existentes.
