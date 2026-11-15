# Sistema de Monitorías — backend Flask + MySQL

Este proyecto conserva las páginas HTML, hojas CSS, logo y estructura visual originales, y agrega un backend Flask conectado a la base de datos existente. **No crea ni reemplaza la base de datos automáticamente.**

## 1. Requisitos
- Python 3.10 o superior
- MySQL Server en ejecución y tu base de datos importada en MySQL Workbench
- Una cuenta MySQL con permisos sobre esa base

## 2. Instalar en Windows / PowerShell
Desde la carpeta que contiene `app.py`:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y coloca los datos reales. `DB_NAME` debe ser el nombre exacto de tu base existente.

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_clave_mysql
DB_NAME=monitorias
SECRET_KEY=pon_una_clave_larga_aleatoria
FLASK_DEBUG=true
```

No compartas el archivo `.env` ni subas la contraseña a repositorios.

## 3. Comprobar la conexión

```powershell
python app.py
```

Abre `http://127.0.0.1:5000/api/health`. Si responde `{"estado":"ok", ...}`, Flask pudo conectarse a MySQL. Luego abre `http://127.0.0.1:5000`.

## 4. Contraseñas y primer usuario
El login compara hashes seguros generados con Werkzeug. La columna `usuario.contrasena` debe contener un hash, no texto plano. Para generar uno:

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('CambiaEstaClave123!'))"
```

Copia el hash resultante a la columna `contrasena` del usuario de prueba y asegúrate de asignarle un registro en `rol_usuario`. El proyecto no crea usuarios administradores ficticios.

## 5. Esquema y migración opcional
El volcado SQL compartido contiene las tablas `usuario`, `rol`, `rol_usuario`, `estudiante`, `profesor`, `monitor`, `jefe_bienestar`, `administrador`, `asignacion_monitoria`, `sesion_monitoria`, `mensaje` y `seguimiento_academico`.

El volcado no contiene `solicitud_monitoria` ni `historial_asignacion`, aunque el frontend original contempla solicitudes e historial. Para activar esas funcionalidades persistentes, abre `migrations/001_funcionalidades_opcionales.sql` en MySQL Workbench, selecciona tu base existente y ejecútalo **solo después de hacer respaldo**. Este archivo no crea la base de datos y no elimina datos.

La estructura original y el dump tienen diferencias. Este backend usa las columnas que aparecen en el dump. No ejecuta automáticamente `schema.sql` del frontend porque ese archivo contiene cambios adicionales y podría no coincidir con tu instalación.

## 6. Endpoints implementados
- `POST /login`, `POST /logout`, `GET /seleccionar-rol`, `POST /cambiar-rol`
- `GET /api/yo`, `GET /api/health`
- `GET/POST /api/usuarios` (administrador)
- `GET /api/docentes`, `GET /api/monitores`
- `GET /api/asignaciones`, `PATCH /api/asignaciones/<id>/estado`
- `GET/POST /api/solicitudes`, `PATCH /api/solicitudes/<id>` (requiere la migración opcional)
- `GET/POST /api/sesiones/<id_asignacion>`
- `GET /api/mensajes/<id_usuario>`, `POST /api/mensajes`
- `GET /api/seguimiento/<id_estudiante>`, `POST /api/seguimiento`

Las rutas JSON esperan cuerpos JSON en las operaciones `POST`/`PATCH`. Los endpoints aplican sesión y comprobaciones de rol básicas; antes de publicar el sistema en internet, añade CSRF para formularios, limitación de intentos de login, configuración HTTPS y revisión de permisos por cada operación.

## 7. Estado real de la migración
El backend Python y las rutas de datos están creados, y las páginas HTML/CSS originales se conservan. **No todos los scripts JavaScript originales han sido sustituidos ni todos los formularios están conectados a los endpoints**: varios scripts originales guardaban datos en `localStorage` y requieren adaptar sus eventos `fetch()` para enviar/recibir datos de Flask. No borres la carpeta `js` hasta terminar esa conexión y probar cada flujo.
