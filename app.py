import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from mysql.connector import Error
from db import get_connection

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CAMBIA_ESTA_CLAVE_ANTES_DE_USAR_EN_PRODUCCION")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "false").lower() == "true"

PAGE_TEMPLATES = {
    "admin/admin.html": "admin",
    "admin/admin_asignaciones.html": "admin",
    "admin/admin_monitorias.html": "admin",
    "admin/admin_reportes.html": "admin",
    "admin/admin_usuarios.html": "admin",
    "admin/admin_crear_usuario.html": "admin",
    "docente/docente.html": "profesor",
    "docente/docente_alertas.html": "profesor",
    "docente/docente_monitores.html": "profesor",
    "docente/docente_reportes.html": "profesor",
    "docente/docente_seguimiento.html": "profesor",
    "docente/docente_solicitudes.html": "profesor",
    "docente/docente_chat.html": "profesor",
    "estudiante/estudiante.html": "estudiante",
    "estudiante/estudiante_mis_monitorias.html": "estudiante",
    "estudiante/estudiante_solicitar.html": "estudiante",
    "estudiante/estudiante_chat.html": "estudiante",
    "monitor/monitor.html": "monitor",
    "monitor/monitor_asignaciones.html": "monitor",
    "monitor/monitor_historial.html": "monitor",
    "monitor/monitor_sesiones.html": "monitor",
    "monitor/monitor_chat.html": "monitor",
    "perfil/perfil.html": None,
    "perfil/perfil_admin.html": "admin",
    "perfil/perfil_docente.html": "profesor",
    "perfil/perfil_estudiante.html": "estudiante",
    "inicio/recuperar_password.html": None,
}


class AppError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)


def db_query(sql, params=(), one=False, many=False, commit=False):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        if one:
            return cur.fetchone()
        if many:
            return cur.fetchall()
        return None
    except Error as exc:
        conn.rollback()
        raise AppError("No se pudo completar la operación en la base de datos. Verifica tablas, columnas y datos.", 400) from exc
    finally:
        cur.close()
        conn.close()


def tiene_permiso(roles, requerido):
    actual = {str(r).strip().lower() for r in roles if r}
    requerido = str(requerido).strip().lower()
    if requerido in ("admin", "administrador"):
        return bool(actual.intersection({"jefe", "admin", "administrador"}))
    return requerido in actual


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify(error="Debes iniciar sesión."), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            disponibles = session.get("roles", [])
            activo = session.get("rol_activo")
            if len(disponibles) > 1 and not activo:
                if request.path.startswith("/api/"):
                    return jsonify(error="Selecciona un perfil antes de continuar."), 403
                return redirect(url_for("seleccionar_rol"))
            efectivos = [activo] if activo else disponibles
            if not any(tiene_permiso(efectivos, r) for r in roles):
                if request.path.startswith("/api/"):
                    return jsonify(error="No tienes permisos para esta acción."), 403
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco


def get_roles(uid):
    rows = db_query(
        """SELECT r.nombre_rol FROM rol_usuario ru
        JOIN rol r ON r.id_rol=ru.id_rol WHERE ru.id_usuario=%s
        ORDER BY r.nombre_rol""",
        (uid,), many=True
    )
    return [row["nombre_rol"] for row in rows]


def selected_role():
    return (session.get("rol_activo") or "").lower()


@app.get("/")
def index():
    if session.get("user_id"):
        if len(session.get("roles", [])) > 1 and not session.get("rol_activo"):
            return redirect(url_for("seleccionar_rol"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("inicio/login.html")
    ident = (request.form.get("usuario") or "").strip()
    if "@" in ident:
        ident = ident.lower()
    password = request.form.get("contrasena") or ""
    if not ident or not password:
        flash("Ingresa tu documento o correo y tu contraseña.", "error")
        return redirect(url_for("login"))

    user = db_query(
        """SELECT id_usuario,documento,nombres,apellidos,correo_institucional,contrasena,estado
        FROM usuario WHERE documento=%s OR correo_institucional=%s LIMIT 1""",
        (ident, ident), one=True
    )
    if not user or not check_password_hash(user["contrasena"], password):
        flash("Credenciales incorrectas.", "error")
        return redirect(url_for("login"))

    if user.get("estado") == "Inactivo":
        flash("Tu cuenta se encuentra inactiva. Contacta al administrador.", "error")
        return redirect(url_for("login"))

    roles = get_roles(user["id_usuario"])
    if not roles:
        flash("Tu cuenta no tiene roles asignados. Contacta al responsable del sistema.", "error")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user["id_usuario"]
    session["nombre"] = f'{user["nombres"]} {user["apellidos"]}'
    session["correo"] = user["correo_institucional"]
    session["roles"] = roles
    if len(roles) == 1:
        session["rol_activo"] = roles[0]
    return redirect(url_for("seleccionar_rol") if len(roles) > 1 else url_for("dashboard"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("inicio/registro.html")
    return redirect(url_for("login"))


@app.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "GET":
        return render_template("inicio/recuperar_password.html")
    
    identificador = (request.form.get("identificador") or "").strip()
    if "@" in identificador:
        identificador = identificador.lower()

    nueva = request.form.get("nueva_contrasena") or ""
    confirmar = request.form.get("confirmar_contrasena") or ""

    if not identificador or not nueva or not confirmar:
        flash("Todos los campos son obligatorios.", "error")
        return redirect(url_for("recuperar_password"))

    if nueva != confirmar:
        flash("Las contraseñas nuevas no coinciden.", "error")
        return redirect(url_for("recuperar_password"))

    if len(nueva) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("recuperar_password"))

    user = db_query(
        "SELECT id_usuario FROM usuario WHERE documento = %s OR correo_institucional = %s LIMIT 1",
        (identificador, identificador), one=True
    )

    if not user:
        flash("No se encontró ningún usuario con ese documento o correo.", "error")
        return redirect(url_for("recuperar_password"))

    try:
        nueva_hash = generate_password_hash(nueva)
        db_query("UPDATE usuario SET contrasena = %s WHERE id_usuario = %s", (nueva_hash, user["id_usuario"]), commit=True)
        flash("¡Contraseña restablecida con éxito! Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))
    except Exception as exc:
        flash(f"Error al actualizar la contraseña: {exc}", "error")
        return redirect(url_for("recuperar_password"))


@app.post("/perfil/cambiar-contrasena")
@login_required
def cambiar_contrasena_perfil():
    uid = session.get("user_id")
    actual = request.form.get("contrasena_actual") or ""
    nueva = request.form.get("contrasena_nueva") or ""
    confirmar = request.form.get("contrasena_confirmar") or ""

    if not actual or not nueva or not confirmar:
        flash("Todos los campos de contraseña son obligatorios.", "error")
        return redirect(url_for("pages", page="perfil/perfil.html"))

    if nueva != confirmar:
        flash("Las nuevas contraseñas no coinciden.", "error")
        return redirect(url_for("pages", page="perfil/perfil.html"))

    if len(nueva) < 8:
        flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("pages", page="perfil/perfil.html"))

    user = db_query("SELECT contrasena FROM usuario WHERE id_usuario = %s", (uid,), one=True)
    if not user or not check_password_hash(user["contrasena"], actual):
        flash("La contraseña actual es incorrecta.", "error")
        return redirect(url_for("pages", page="perfil/perfil.html"))

    try:
        nueva_hash = generate_password_hash(nueva)
        db_query("UPDATE usuario SET contrasena = %s WHERE id_usuario = %s", (nueva_hash, uid), commit=True)
        flash("Contraseña actualizada correctamente.", "success")
    except Exception as exc:
        flash(f"Error al actualizar la contraseña: {exc}", "error")

    return redirect(url_for("pages", page="perfil/perfil.html"))


@app.get("/seleccionar-rol")
@login_required
def seleccionar_rol():
    return render_template("inicio/seleccionar_rol.html", roles=session.get("roles", []))


@app.post("/cambiar-rol")
@login_required
def cambiar_rol():
    rol = (request.form.get("rol") or "").strip()
    if rol not in session.get("roles", []):
        flash("Ese perfil no está disponible para tu cuenta.", "error")
        return redirect(url_for("seleccionar_rol"))
    session["rol_activo"] = rol
    return redirect(url_for("dashboard"))


@app.post("/logout")
@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    roles = session.get("roles", [])
    if len(roles) > 1 and not session.get("rol_activo"):
        return redirect(url_for("seleccionar_rol"))
    role = selected_role() or (roles[0].lower() if roles else "")
    destinos = {
        "estudiante": "estudiante/estudiante.html",
        "monitor": "monitor/monitor.html",
        "profesor": "docente/docente.html",
        "jefe": "admin/admin.html",
        "admin": "admin/admin.html",
        "administrador": "admin/admin.html",
    }
    if role not in destinos:
        abort(403)
    return redirect("/" + destinos[role])


# --- RUTA PARA CREAR USUARIOS DESDE EL ADMIN ---
@app.post("/admin/usuarios/crear")
@role_required("Admin", "Administrador")
def crear_usuario_admin():
    documento = (request.form.get("documento") or "").strip()
    nombres = (request.form.get("nombres") or "").strip()
    apellidos = (request.form.get("apellidos") or "").strip()
    telefono = (request.form.get("telefono") or "").strip()
    correo = (request.form.get("correo_institucional") or "").strip().lower()
    contrasena = request.form.get("contrasena") or ""
    rol = (request.form.get("rol") or "").strip()
    
    semestre = 1
    programa = (request.form.get("programa_academico") or "").strip()
    facultad = (request.form.get("facultad") or "").strip()
    departamento = (request.form.get("departamento") or "").strip()
    oficina = (request.form.get("oficina") or "").strip()
    categoria = (request.form.get("categoria_docente") or "").strip()

    if not documento.isdigit() or not (6 <= len(documento) <= 12):
        flash("El documento debe tener entre 6 y 12 dígitos.", "error")
        return redirect(url_for("pages", page="admin/admin_crear_usuario.html"))
    
    if len(contrasena) < 8:
        flash("La contraseña debe tener al menos 8 caracteres.", "error")
        return redirect(url_for("pages", page="admin/admin_crear_usuario.html"))

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id_rol FROM rol WHERE LOWER(nombre_rol) LIKE LOWER(%s) LIMIT 1", (f"%{rol}%",))
        rol_db = cur.fetchone()
        if not rol_db:
            flash("El rol seleccionado no es válido.", "error")
            return redirect(url_for("pages", page="admin/admin_crear_usuario.html"))

        cur.execute(
            """INSERT INTO usuario (documento, nombres, apellidos, correo_institucional, contrasena, telefono, estado)
               VALUES (%s, %s, %s, %s, %s, %s, 'Activo')""",
            (documento, nombres, apellidos, correo, generate_password_hash(contrasena), telefono or None)
        )
        uid = cur.lastrowid

        cur.execute("INSERT INTO rol_usuario (id_usuario, id_rol) VALUES (%s, %s)", (uid, rol_db["id_rol"]))

        rol_lower = rol.lower()
        if "estudiante" in rol_lower:
            cur.execute(
                """INSERT INTO estudiante (id_usuario, semestre_actual, programa_academico, promedio_ponderado)
                   VALUES (%s, %s, %s, 0.00)""",
                (uid, semestre, programa or "Ingeniería de Sistemas")
            )
        elif "profesor" in rol_lower or "docente" in rol_lower:
            cur.execute(
                """INSERT INTO profesor (id_usuario, facultad, departamento, oficina, categoria_docente)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    uid, 
                    facultad or "Facultad de Ingeniería", 
                    departamento or "Departamento General", 
                    oficina or None, 
                    categoria or "Planta"
                )
            )

        conn.commit()
        flash("Usuario creado correctamente en la base de datos.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error al registrar el usuario: {exc}", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("pages", page="admin/admin_usuarios.html"))


# --- RUTA PARA INHABILITAR O ACTIVAR UN USUARIO GLOBAL ---
@app.post("/admin/usuarios/<int:uid>/estado")
@role_required("Admin", "Administrador")
def cambiar_estado_usuario(uid):
    user = db_query("SELECT estado FROM usuario WHERE id_usuario = %s", (uid,), one=True)
    if not user:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("pages", page="admin/admin_usuarios.html"))
    
    nuevo_estado = "Inactivo" if user.get("estado") == "Activo" or not user.get("estado") else "Activo"
    db_query("UPDATE usuario SET estado = %s WHERE id_usuario = %s", (nuevo_estado, uid), commit=True)
    flash(f"El estado de la cuenta ha cambiado a: {nuevo_estado}", "success")
    return redirect(url_for("pages", page="admin/admin_usuarios.html"))


# --- RUTA PARA ASCENDER O REACTIVAR A UN MONITOR ---
@app.post("/admin/usuarios/<int:uid>/ascender-monitor")
@role_required("Admin", "Administrador")
def ascender_a_monitor(uid):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id_rol FROM rol WHERE LOWER(nombre_rol) = 'monitor' LIMIT 1")
        rol_monitor = cur.fetchone()
        if not rol_monitor:
            flash("No existe el rol 'Monitor' configurado en la base de datos.", "error")
            return redirect(url_for("pages", page="admin/admin_usuarios.html"))

        cur.execute("SELECT * FROM rol_usuario WHERE id_usuario = %s AND id_rol = %s", (uid, rol_monitor["id_rol"]))
        if not cur.fetchone():
            cur.execute("INSERT INTO rol_usuario (id_usuario, id_rol) VALUES (%s, %s)", (uid, rol_monitor["id_rol"]))

        cur.execute("SELECT * FROM monitor WHERE id_usuario = %s", (uid,))
        if not cur.fetchone():
            cur.execute(
                """INSERT INTO monitor (id_usuario, area_en_que_brindara_el_apoyo, promedio_acumulado, horas_asignadas, estado)
                   VALUES (%s, 'Apoyo General', 0.00, 0, 'Activo')""",
                (uid,)
            )
        else:
            cur.execute("UPDATE monitor SET estado = 'Activo' WHERE id_usuario = %s", (uid,))

        conn.commit()
        flash("El estudiante ha sido asignado/reactivado como Monitor correctamente.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error al cambiar estado de monitor: {exc}", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("pages", page="admin/admin_usuarios.html"))


# --- RUTA PARA INHABILITAR A UN MONITOR ---
@app.post("/admin/usuarios/<int:uid>/revocar-monitor")
@role_required("Admin", "Administrador")
def revocar_monitor(uid):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("UPDATE monitor SET estado = 'Inactivo' WHERE id_usuario = %s", (uid,))
        cur.execute("SELECT id_rol FROM rol WHERE LOWER(nombre_rol) = 'monitor' LIMIT 1")
        rol_monitor = cur.fetchone()
        if rol_monitor:
            cur.execute("DELETE FROM rol_usuario WHERE id_usuario = %s AND id_rol = %s", (uid, rol_monitor["id_rol"]))

        conn.commit()
        flash("El rol de monitor ha sido inhabilitado. El historial académico del usuario se conservó intacto.", "success")
    except Exception as exc:
        conn.rollback()
        flash(f"Error al inhabilitar monitor: {exc}", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for("pages", page="admin/admin_usuarios.html"))


# --- RUTA PARA SOLICITUD DE MONITORÍA DESDE EL ESTUDIANTE ---
@app.post("/estudiante/solicitar")
@role_required("Estudiante")
def crear_solicitud_estudiante():
    uid = session.get("user_id")
    materia = (request.form.get("materia") or "").strip()
    tipo_apoyo = request.form.get("tipo_apoyo")
    id_docente = request.form.get("id_docente")
    fecha = request.form.get("fecha_preferida")
    horario = request.form.get("horario")
    modalidad = request.form.get("modalidad", "Presencial")
    detalle = request.form.get("detalle")

    if not all([materia, tipo_apoyo, id_docente, fecha, horario]):
        flash("Completa todos los campos obligatorios de la solicitud.", "error")
        return redirect(url_for("pages", page="estudiante/estudiante_solicitar.html"))

    try:
        db_query(
            """INSERT INTO solicitud_monitoria 
               (id_estudiante, id_docente, materia, tipo_apoyo, fecha_preferida, horario, modalidad, detalle, estado)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente')""",
            (uid, id_docente, materia, tipo_apoyo, fecha, horario, modalidad, detalle),
            commit=True
        )
        flash("Solicitud de monitoría enviada con éxito.", "success")
        return redirect(url_for("pages", page="estudiante/estudiante_mis_monitorias.html"))
    except Exception as exc:
        flash(f"Error al enviar la solicitud: {exc}", "error")
        return redirect(url_for("pages", page="estudiante/estudiante_solicitar.html"))


# --- RUTA PARA QUE EL DOCENTE ASIGNE MONITOR ---
@app.post("/docente/solicitudes/<int:id_solicitud>/asignar")
@role_required("Profesor", "Docente")
def asignar_monitor_docente(id_solicitud):
    uid = session.get("user_id")
    id_monitor = request.form.get("id_monitor")
    
    if not id_monitor:
        flash("Debes seleccionar un monitor de la lista para hacer la asignación.", "error")
        return redirect(url_for("pages", page="docente/docente_solicitudes.html"))

    try:
        db_query(
            """UPDATE solicitud_monitoria 
               SET estado = 'Aprobada', id_monitor = %s 
               WHERE id_solicitud = %s AND id_docente = %s""",
            (id_monitor, id_solicitud, uid),
            commit=True
        )
        flash("Monitor asignado correctamente. La solicitud pasó al registro general.", "success")
    except Exception as exc:
        flash(f"Error al asignar el monitor: {exc}", "error")

    return redirect(url_for("pages", page="docente/docente_solicitudes.html"))


# --- RUTA PARA QUE EL MONITOR ACTUALICE EL ESTADO DE SU MONITORÍA ASIGNADA ---
@app.post("/monitor/monitorias/<int:id_solicitud>/actualizar")
@role_required("Monitor")
def actualizar_monitoria_monitor(id_solicitud):
    uid = session.get("user_id")
    nuevo_estado = (request.form.get("estado") or "").strip()
    
    try:
        db_query(
            """UPDATE solicitud_monitoria 
               SET estado = %s 
               WHERE id_solicitud = %s AND id_monitor = %s""",
            (nuevo_estado, id_solicitud, uid),
            commit=True
        )
        flash(f"El estado de la monitoría se actualizó a: {nuevo_estado}", "success")
    except Exception as exc:
        flash(f"Error al actualizar la monitoría: {exc}", "error")

    return redirect(url_for("pages", page="monitor/monitor_historial.html"))


# --- RUTA PARA QUE EL MONITOR GUARDE UNA SESIÓN ---
@app.post("/monitor/sesiones/guardar")
@role_required("Monitor")
def guardar_sesion_monitor():
    uid = session.get("user_id")
    id_solicitud = request.form.get("id_solicitud")
    fecha_sesion = request.form.get("fecha_sesion")
    asistencia = request.form.get("asistencia", "Presente")
    avance = request.form.get("avance_estudiante")
    observaciones = request.form.get("observaciones_monitor")

    if not id_solicitud or not fecha_sesion:
        flash("Selecciona la monitoría y la fecha de la sesión.", "error")
        return redirect(url_for("pages", page="monitor/monitor_sesiones.html"))

    try:
        db_query(
            """INSERT INTO sesion_monitoria (id_asignacion, fecha_sesion, asistencia, avance_estudiante, observaciones_monitor)
               VALUES (%s, %s, %s, %s, %s)""",
            (id_solicitud, fecha_sesion, asistencia, avance, observaciones),
            commit=True
        )
        flash("Sesión de monitoría registrada con éxito.", "success")
    except Exception as exc:
        flash(f"Error al registrar la sesión: {exc}", "error")

    return redirect(url_for("pages", page="monitor/monitor_sesiones.html"))


# --- RUTAS DE MENSAJERÍA ---
@app.post("/chat/enviar")
@login_required
def enviar_mensaje():
    remitente_id = session.get("user_id")
    destinatario_id = request.form.get("id_destinatario")
    contenido = (request.form.get("contenido") or "").strip()

    if destinatario_id and contenido:
        db_query(
            """INSERT INTO mensaje (id_remitente, id_destinatario, contenido)
               VALUES (%s, %s, %s)""",
            (remitente_id, destinatario_id, contenido),
            commit=True
        )
    return redirect(url_for("pages", page="estudiante/estudiante_chat.html") + f"?chat_con={destinatario_id}")


@app.post("/docente/chat/enviar")
@login_required
def enviar_mensaje_docente():
    remitente_id = session.get("user_id")
    destinatario_id = request.form.get("id_destinatario")
    contenido = (request.form.get("contenido") or "").strip()
    if destinatario_id and contenido:
        db_query(
            """INSERT INTO mensaje (id_remitente, id_destinatario, contenido) 
               VALUES (%s, %s, %s)""",
            (remitente_id, destinatario_id, contenido),
            commit=True
        )
    return redirect(url_for("pages", page="docente/docente_chat.html") + f"?chat_con={destinatario_id}")


# --- RUTA PARA SEGUIMIENTO ACADÉMICO ---
@app.post("/docente/seguimiento/guardar")
@role_required("Profesor", "Docente")
def guardar_seguimiento_docente():
    estudiante_id = request.form.get("id_estudiante")
    momento = request.form.get("momento_o_corte")
    promedio = request.form.get("calificacion_promedio")
    observacion = request.form.get("observacion_docente")
    alerta = request.form.get("alerta_activa", "No")

    if not estudiante_id or not observacion:
        flash("Selecciona un estudiante y escribe la observación.", "error")
        return redirect(url_for("pages", page="docente/docente_seguimiento.html"))

    try:
        db_query(
            """INSERT INTO seguimiento_academico 
               (id_estudiante, momento_o_corte, calificacion_promedio, observacion_docente, alerta_activa)
               VALUES (%s, %s, %s, %s, %s)""",
            (estudiante_id, momento, promedio or None, observacion, alerta),
            commit=True
        )
        flash("Seguimiento académico registrado con éxito.", "success")
    except Exception as exc:
        flash(f"Error al registrar seguimiento: {exc}", "error")

    return redirect(url_for("pages", page="docente/docente_seguimiento.html"))


@app.get("/<path:page>")
def pages(page):
    if page not in PAGE_TEMPLATES:
        if page == "index.html":
            return redirect(url_for("login"))
        abort(404)
        
    requerido = PAGE_TEMPLATES[page]
    if requerido and not session.get("user_id"):
        return redirect(url_for("login"))
        
    roles = [session.get("rol_activo")] if session.get("rol_activo") else session.get("roles", [])
    if requerido and not tiene_permiso(roles, requerido):
        abort(403)

    extra_data = {}

    try:
        if page == "admin/admin.html":
            extra_data["total_estudiantes"] = db_query("SELECT COUNT(*) AS total FROM estudiante", one=True)["total"]
            extra_data["total_monitores"] = db_query("SELECT COUNT(*) AS total FROM monitor WHERE estado='Activo'", one=True)["total"]
            extra_data["monitorias_activas"] = db_query("SELECT COUNT(*) AS total FROM solicitud_monitoria WHERE estado='Aprobada'", one=True)["total"]
            extra_data["total_tutorias"] = db_query("SELECT COUNT(*) AS total FROM sesion_monitoria", one=True)["total"]
            extra_data["total_alertas"] = db_query("SELECT COUNT(*) AS total FROM seguimiento_academico WHERE alerta_activa='Sí'", one=True)["total"]
            extra_data["usuarios_resumen"] = db_query(
                """SELECT u.id_usuario, u.documento, u.nombres, u.apellidos, u.correo_institucional, 
                          GROUP_CONCAT(r.nombre_rol SEPARATOR ', ') AS rol
                   FROM usuario u 
                   LEFT JOIN rol_usuario ru ON ru.id_usuario = u.id_usuario
                   LEFT JOIN rol r ON r.id_rol = ru.id_rol
                   GROUP BY u.id_usuario LIMIT 5""", many=True
            )

        elif page == "admin/admin_usuarios.html":
            extra_data["usuarios"] = db_query(
                """SELECT u.id_usuario, u.documento, u.nombres, u.apellidos, u.correo_institucional, 
                          u.telefono, u.estado,
                          (SELECT m.estado FROM monitor m WHERE m.id_usuario = u.id_usuario) AS estado_monitor,
                          GROUP_CONCAT(r.nombre_rol ORDER BY r.nombre_rol SEPARATOR ', ') AS rol
                   FROM usuario u 
                   LEFT JOIN rol_usuario ru ON ru.id_usuario = u.id_usuario
                   LEFT JOIN rol r ON r.id_rol = ru.id_rol
                   GROUP BY u.id_usuario
                   ORDER BY u.apellidos, u.nombres""", many=True
            )

        elif page == "admin/admin_reportes.html":
            extra_data["total_alertas"] = db_query("SELECT COUNT(*) AS total FROM seguimiento_academico WHERE alerta_activa='Sí'", one=True)["total"]
            extra_data["total_solicitudes"] = db_query("SELECT COUNT(*) AS total FROM solicitud_monitoria", one=True)["total"]
            extra_data["total_sesiones"] = db_query("SELECT COUNT(*) AS total FROM sesion_monitoria", one=True)["total"]
            
            extra_data["alertas_detalladas"] = db_query(
                """SELECT seg.*, CONCAT(u.nombres, ' ', u.apellidos) AS estudiante, u.correo_institucional
                   FROM seguimiento_academico seg
                   JOIN usuario u ON u.id_usuario = seg.id_estudiante
                   WHERE seg.alerta_activa = 'Sí'
                   ORDER BY seg.id_seguimiento DESC""",
                many=True
            )

            extra_data["estado_solicitudes"] = db_query(
                """SELECT estado, COUNT(*) AS cantidad 
                   FROM solicitud_monitoria 
                   GROUP BY estado""",
                many=True
            )

        elif page == "estudiante/estudiante_mis_monitorias.html":
            uid = session.get("user_id")
            extra_data["mis_monitorias"] = db_query(
                """SELECT s.id_solicitud, s.materia, s.modalidad, s.estado,
                          CONCAT(d.nombres, ' ', d.apellidos) AS docente
                   FROM solicitud_monitoria s
                   JOIN usuario d ON d.id_usuario = s.id_docente
                   WHERE s.id_estudiante = %s
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )

        elif page == "estudiante/estudiante_solicitar.html":
            uid = session.get("user_id")
            
            # Obtener el programa académico del estudiante logueado
            estudiante_info = db_query("SELECT programa_academico FROM estudiante WHERE id_usuario = %s", (uid,), one=True)
            programa_estudiante = estudiante_info["programa_academico"] if estudiante_info else ""

            # Determinar la facultad correspondiente al programa del estudiante
            facultad_filtro = "Facultad de Ingeniería"
            if "Derecho" in programa_estudiante:
                facultad_filtro = "Facultad de Derecho"
            elif "Contaduría" in programa_estudiante or "Administración" in programa_estudiante:
                facultad_filtro = "Facultad de Ciencias Económicas y Administrativas"
            elif "Psicología" in programa_estudiante:
                facultad_filtro = "Facultad de Psicología"
            elif "Enfermería" in programa_estudiante:
                facultad_filtro = "Facultad de Ciencias de la Salud"

            # Filtrar docentes de la misma facultad
            extra_data["docentes"] = db_query(
                """SELECT u.id_usuario, u.nombres, u.apellidos, p.departamento 
                   FROM profesor p 
                   JOIN usuario u ON u.id_usuario = p.id_usuario
                   WHERE p.facultad = %s""",
                (facultad_filtro,),
                many=True
            )

        elif page == "estudiante/estudiante_chat.html":
            uid = session.get("user_id")
            extra_data["todos_usuarios"] = db_query(
                "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario != %s",
                (uid,), many=True
            )
            chat_con = request.args.get("chat_con")
            if chat_con:
                extra_data["contacto_activo"] = db_query(
                    "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario = %s",
                    (chat_con,), one=True
                )
                extra_data["mensajes"] = db_query(
                    """SELECT * FROM mensaje 
                       WHERE (id_remitente = %s AND id_destinatario = %s) 
                          OR (id_remitente = %s AND id_destinatario = %s)
                       ORDER BY fecha_envio ASC""",
                    (uid, chat_con, chat_con, uid), many=True
                )

        elif page == "docente/docente.html":
            uid = session.get("user_id")
            
            profesor_info = db_query("SELECT facultad FROM profesor WHERE id_usuario = %s", (uid,), one=True)
            facultad_docente = profesor_info["facultad"] if profesor_info else ""

            extra_data["total_solicitudes"] = db_query("SELECT COUNT(*) AS total FROM solicitud_monitoria WHERE id_docente = %s", (uid,), one=True)["total"]
            
            monitor_count_res = db_query(
                """SELECT COUNT(*) AS total 
                   FROM monitor mo
                   JOIN estudiante est ON est.id_usuario = mo.id_usuario
                   WHERE mo.estado = 'Activo' 
                     AND (est.programa_academico = %s OR mo.area_en_que_brindara_el_apoyo LIKE %s)""",
                (facultad_docente, f"%{facultad_docente}%"),
                one=True
            )
            extra_data["total_monitores"] = monitor_count_res["total"] if monitor_count_res else 0

        elif page == "docente/docente_solicitudes.html":
            uid = session.get("user_id")
            
            profesor_info = db_query("SELECT facultad FROM profesor WHERE id_usuario = %s", (uid,), one=True)
            facultad_docente = profesor_info["facultad"] if profesor_info else ""

            extra_data["solicitudes_pendientes"] = db_query(
                """SELECT s.id_solicitud, s.materia, s.tipo_apoyo, s.fecha_preferida, s.horario, s.modalidad, s.detalle,
                          CONCAT(e.nombres, ' ', e.apellidos) AS estudiante
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   WHERE s.id_docente = %s AND (s.id_monitor IS NULL OR s.estado = 'Pendiente')
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )
            extra_data["monitorias_asignadas"] = db_query(
                """SELECT s.id_solicitud, s.materia, s.tipo_apoyo, s.fecha_preferida, s.horario, s.modalidad, s.estado,
                          CONCAT(e.nombres, ' ', e.apellidos) AS estudiante,
                          CONCAT(m.nombres, ' ', m.apellidos) AS monitor
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   LEFT JOIN usuario m ON m.id_usuario = s.id_monitor
                   WHERE s.id_docente = %s AND s.id_monitor IS NOT NULL
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )
            
            extra_data["monitores_disponibles"] = db_query(
                """SELECT u.id_usuario, CONCAT(u.nombres, ' ', u.apellidos) AS nombre_monitor, mo.area_en_que_brindara_el_apoyo
                   FROM monitor mo
                   JOIN usuario u ON u.id_usuario = mo.id_usuario
                   JOIN estudiante est ON est.id_usuario = mo.id_usuario
                   WHERE mo.estado = 'Activo' 
                     AND (est.programa_academico = %s OR mo.area_en_que_brindara_el_apoyo LIKE %s)""",
                (facultad_docente, f"%{facultad_docente}%"),
                many=True
            )

        elif page == "docente/docente_monitores.html":
            uid = session.get("user_id")
            
            profesor_info = db_query("SELECT facultad FROM profesor WHERE id_usuario = %s", (uid,), one=True)
            facultad_docente = profesor_info["facultad"] if profesor_info else ""

            extra_data["monitores"] = db_query(
                """SELECT u.id_usuario, u.nombres, u.apellidos, u.correo_institucional, u.telefono,
                          m.area_en_que_brindara_el_apoyo, m.promedio_acumulado, m.horas_asignadas, m.estado
                   FROM monitor m
                   JOIN usuario u ON u.id_usuario = m.id_usuario
                   JOIN estudiante est ON est.id_usuario = m.id_usuario
                   WHERE est.programa_academico = %s OR m.area_en_que_brindara_el_apoyo LIKE %s""",
                (facultad_docente, f"%{facultad_docente}%"),
                many=True
            )

        elif page == "docente/docente_seguimiento.html":
            uid = session.get("user_id")
            
            profesor_info = db_query("SELECT facultad FROM profesor WHERE id_usuario = %s", (uid,), one=True)
            facultad_docente = profesor_info["facultad"] if profesor_info else ""

            extra_data["estudiantes"] = db_query(
                """SELECT u.id_usuario, u.nombres, u.apellidos, e.programa_academico 
                   FROM estudiante e 
                   JOIN usuario u ON u.id_usuario = e.id_usuario
                   WHERE e.programa_academico = %s""",
                (facultad_docente,),
                many=True
            )
            
            extra_data["seguimientos"] = db_query(
                """SELECT seg.*, CONCAT(u.nombres, ' ', u.apellidos) AS estudiante
                   FROM seguimiento_academico seg
                   JOIN usuario u ON u.id_usuario = seg.id_estudiante
                   JOIN estudiante e ON e.id_usuario = seg.id_estudiante
                   WHERE e.programa_academico = %s
                   ORDER BY seg.id_seguimiento DESC""",
                (facultad_docente,),
                many=True
            )

        elif page == "docente/docente_chat.html":
            uid = session.get("user_id")
            extra_data["todos_usuarios"] = db_query(
                "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario != %s",
                (uid,), many=True
            )
            chat_con = request.args.get("chat_con")
            if chat_con:
                extra_data["contacto_activo"] = db_query(
                    "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario = %s",
                    (chat_con,), one=True
                )
                extra_data["mensajes"] = db_query(
                    """SELECT * FROM mensaje 
                       WHERE (id_remitente = %s AND id_destinatario = %s) 
                          OR (id_remitente = %s AND id_destinatario = %s)
                       ORDER BY fecha_envio ASC""",
                    (uid, chat_con, chat_con, uid), many=True
                )

        elif page == "monitor/monitor.html":
            uid = session.get("user_id")
            extra_data["total_asignadas"] = db_query("SELECT COUNT(*) AS total FROM solicitud_monitoria WHERE id_monitor = %s", (uid,), one=True)["total"]
            extra_data["monitorias_activas_inicio"] = db_query(
                """SELECT s.materia, s.estado, CONCAT(e.nombres, ' ', e.apellidos) AS estudiante, CONCAT(d.nombres, ' ', d.apellidos) AS docente
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   JOIN usuario d ON d.id_usuario = s.id_docente
                   WHERE s.id_monitor = %s AND s.estado NOT IN ('Completada', 'Cancelada', 'Rechazada')
                   ORDER BY s.id_solicitud DESC LIMIT 5""",
                (uid,), many=True
            )

        elif page == "monitor/monitor_asignaciones.html":
            uid = session.get("user_id")
            extra_data["mis_asignaciones_lista"] = db_query(
                """SELECT s.materia, s.tipo_apoyo, s.fecha_preferida, s.estado, 
                          CONCAT(e.nombres, ' ', e.apellidos) AS estudiante, 
                          CONCAT(d.nombres, ' ', d.apellidos) AS docente
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   JOIN usuario d ON d.id_usuario = s.id_docente
                   WHERE s.id_monitor = %s
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )

        elif page == "monitor/monitor_sesiones.html":
            uid = session.get("user_id")
            extra_data["monitorias_activas"] = db_query(
                """SELECT s.id_solicitud, s.materia, CONCAT(e.nombres, ' ', e.apellidos) AS estudiante
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   WHERE s.id_monitor = %s AND s.estado = 'Aprobada'""",
                (uid,), many=True
            )

        elif page == "monitor/monitor_historial.html":
            uid = session.get("user_id")
            extra_data["monitorias_pendientes"] = db_query(
                """SELECT s.id_solicitud, s.materia, s.tipo_apoyo, s.fecha_preferida, s.horario, s.modalidad, s.estado, s.detalle,
                          CONCAT(e.nombres, ' ', e.apellidos) AS estudiante,
                          CONCAT(d.nombres, ' ', d.apellidos) AS docente
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   JOIN usuario d ON d.id_usuario = s.id_docente
                   WHERE s.id_monitor = %s AND s.estado NOT IN ('Completada', 'Cancelada', 'Rechazada')
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )
            extra_data["monitorias_historial"] = db_query(
                """SELECT s.id_solicitud, s.materia, s.tipo_apoyo, s.fecha_preferida, s.horario, s.modalidad, s.estado,
                          CONCAT(e.nombres, ' ', e.apellidos) AS estudiante,
                          CONCAT(d.nombres, ' ', d.apellidos) AS docente
                   FROM solicitud_monitoria s
                   JOIN usuario e ON e.id_usuario = s.id_estudiante
                   JOIN usuario d ON d.id_usuario = s.id_docente
                   WHERE s.id_monitor = %s AND s.estado IN ('Completada', 'Cancelada', 'Rechazada')
                   ORDER BY s.id_solicitud DESC""",
                (uid,), many=True
            )

        elif page == "monitor/monitor_chat.html":
            uid = session.get("user_id")
            extra_data["todos_usuarios"] = db_query(
                "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario != %s",
                (uid,), many=True
            )
            chat_con = request.args.get("chat_con")
            if chat_con:
                extra_data["contacto_activo"] = db_query(
                    "SELECT id_usuario, nombres, apellidos, correo_institucional FROM usuario WHERE id_usuario = %s",
                    (chat_con,), one=True
                )
                extra_data["mensajes"] = db_query(
                    """SELECT * FROM mensaje 
                       WHERE (id_remitente = %s AND id_destinatario = %s) 
                          OR (id_remitente = %s AND id_destinatario = %s)
                       ORDER BY fecha_envio ASC""",
                    (uid, chat_con, chat_con, uid), many=True
                )

        elif page.startswith("perfil/"):
            uid = session.get("user_id")
            extra_data["perfil_usuario"] = db_query(
                """SELECT u.id_usuario, u.documento, u.nombres, u.apellidos, u.correo_institucional, u.telefono, u.sexo
                   FROM usuario u WHERE u.id_usuario = %s""",
                (uid,), one=True
            )
            if page == "perfil/perfil_estudiante.html":
                extra_data["perfil_estudiante"] = db_query(
                    """SELECT semestre_actual, programa_academico, promedio_ponderado
                       FROM estudiante WHERE id_usuario = %s""",
                    (uid,), one=True
                )
            if page == "perfil/perfil_docente.html":
                extra_data["perfil_profesor"] = db_query(
                    """SELECT facultad, departamento, oficina, categoria_docente
                       FROM profesor WHERE id_usuario = %s""",
                    (uid,), one=True
                )
            if page == "perfil/perfil_admin.html":
                extra_data["perfil_bienestar"] = db_query(
                    """SELECT extension_telefonica, sede_asignada, area_bienestar, horario_atencion
                       FROM jefe_bienestar WHERE id_usuario = %s""",
                    (uid,), one=True
                )

    except Exception as exc:
        print(f"Error al cargar datos adicionales para {page}: {exc}")
        pass

    return render_template(
        page, 
        usuario=session.get("nombre", ""), 
        rol=session.get("rol_activo", ""),
        **extra_data
    )


@app.get("/api/yo")
@login_required
def api_me():
    return jsonify(id_usuario=session["user_id"], nombre=session["nombre"],
                   correo=session["correo"], roles=session["roles"],
                   rol_activo=session.get("rol_activo"))


@app.get("/api/health")
def health():
    try:
        row = db_query("SELECT DATABASE() AS base, 1 AS ok", one=True)
        return jsonify(estado="ok", mysql=row)
    except Exception:
        return jsonify(estado="error", mensaje="No se pudo conectar a MySQL."), 503


@app.errorhandler(403)
def forbidden(_):
    if request.path.startswith("/api/"):
        return jsonify(error="Acceso denegado."), 403
    return render_template("inicio/error.html"), 403


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify(error="Recurso no encontrado."), 404
    return render_template("inicio/error.html"), 404


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )