-- 1. Tabla USUARIO
CREATE TABLE USUARIO (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    documento VARCHAR(20) UNIQUE NOT NULL,
    nombres VARCHAR(50) NOT NULL,
    apellidos VARCHAR(50) NOT NULL,
    sexo VARCHAR(20),
    correo_institucional VARCHAR(100) UNIQUE NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    telefono VARCHAR(20)
);

-- 2. Tabla Mensaje
CREATE TABLE Mensaje (
    id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
    id_remitente INT NOT NULL,
    id_destinatario INT NOT NULL,
    contenido TEXT NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    leido BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (id_remitente) REFERENCES USUARIO(id_usuario),
    FOREIGN KEY (id_destinatario) REFERENCES USUARIO(id_usuario)
);

-- 3. Tabla ESTUDIANTE (Herencia de USUARIO)
CREATE TABLE ESTUDIANTE (
    id_usuario INT PRIMARY KEY,
    semestre_actual INT,
    programa_academico VARCHAR(100),
    promedio_ponderado DECIMAL(3,2),
    FOREIGN KEY (id_usuario) REFERENCES USUARIO(id_usuario) ON DELETE CASCADE
);

-- 4. Tabla PROFESOR (Herencia de USUARIO)
CREATE TABLE PROFESOR (
    id_usuario INT PRIMARY KEY,
    facultad VARCHAR(100),
    departamento VARCHAR(100),
    oficina VARCHAR(50),
    categoria_docente VARCHAR(50),
    FOREIGN KEY (id_usuario) REFERENCES USUARIO(id_usuario) ON DELETE CASCADE
);

-- 5. Tabla ADMINISTRADOR (Herencia de USUARIO)
CREATE TABLE ADMINISTRADOR (
    id_usuario INT PRIMARY KEY,
    nivel_acceso VARCHAR(50),
    ultimo_acceso_sistema DATETIME,
    FOREIGN KEY (id_usuario) REFERENCES USUARIO(id_usuario) ON DELETE CASCADE
);

-- 6. Tabla MONITOR (Herencia de ESTUDIANTE)
CREATE TABLE MONITOR (
    id_usuario INT PRIMARY KEY,
    area_en_que_brindara_el_apoyo VARCHAR(100),
    promedio_acumulado DECIMAL(3,2),
    horas_asignadas INT,
    FOREIGN KEY (id_usuario) REFERENCES ESTUDIANTE(id_usuario) ON DELETE CASCADE
);

-- 7. Tabla ESTUDIANTE_CON_MONITORIA (Herencia de ESTUDIANTE)
CREATE TABLE ESTUDIANTE_CON_MONITORIA (
    id_usuario INT PRIMARY KEY,
    tipo_apoyo_requerido VARCHAR(100),
    promedio_acumulado DECIMAL(3,2),
    horas_asignadas INT,
    FOREIGN KEY (id_usuario) REFERENCES ESTUDIANTE(id_usuario) ON DELETE CASCADE
);

-- 8. Tabla JEFE_BIENESTAR (Herencia de PROFESOR)
CREATE TABLE JEFE_BIENESTAR (
    id_usuario INT PRIMARY KEY,
    extension_telefonica VARCHAR(20),
    sede_asignada VARCHAR(100),
    area_bienestar VARCHAR(100),
    horario_atencion VARCHAR(100),
    FOREIGN KEY (id_usuario) REFERENCES PROFESOR(id_usuario) ON DELETE CASCADE
);

-- 9. Tabla SEGUIMIENTO_ACADEMICO
CREATE TABLE SEGUIMIENTO_ACADEMICO (
    id_seguimiento INT AUTO_INCREMENT PRIMARY KEY,
    id_estudiante INT NOT NULL,
    momento_o_corte VARCHAR(50),
    calificacion_promedio DECIMAL(3,2),
    observacion_docente TEXT,
    alerta_activa VARCHAR(5),
    FOREIGN KEY (id_estudiante) REFERENCES ESTUDIANTE(id_usuario) ON DELETE CASCADE
);

-- 10. Tabla ASIGNACION_MONITORIA
CREATE TABLE ASIGNACION_MONITORIA (
    id_asignacion INT AUTO_INCREMENT PRIMARY KEY,
    id_estudiante INT NOT NULL,
    id_docente INT NOT NULL,
    id_monitor INT NOT NULL,
    id_bienestar INT NOT NULL,
    tipo_apoyo VARCHAR(100),
    estado_asignacion VARCHAR(50),
    fecha_asignacion DATE,
    FOREIGN KEY (id_estudiante) REFERENCES ESTUDIANTE(id_usuario),
    FOREIGN KEY (id_docente) REFERENCES PROFESOR(id_usuario),
    FOREIGN KEY (id_monitor) REFERENCES MONITOR(id_usuario),
    FOREIGN KEY (id_bienestar) REFERENCES JEFE_BIENESTAR(id_usuario)
);

-- 11. Tabla SESION_MONITORIA
CREATE TABLE SESION_MONITORIA (
    id_sesion INT AUTO_INCREMENT PRIMARY KEY,
    id_asignacion INT NOT NULL,
    fecha_sesion DATETIME,
    asistencia VARCHAR(20),
    avance_estudiante TEXT,
    observaciones_monitor TEXT,
    FOREIGN KEY (id_asignacion) REFERENCES ASIGNACION_MONITORIA(id_asignacion) ON DELETE CASCADE
);


-- ===== Cambios de esta versión =====

-- 12. USUARIO: nunca se elimina, se inactiva (se conservan estudiantes, docentes y monitores)
ALTER TABLE USUARIO
    ADD COLUMN estado_cuenta ENUM('Activo','Inactivo') NOT NULL DEFAULT 'Activo',
    ADD COLUMN fecha_inactivacion DATE NULL;

-- 13. ASIGNACION_MONITORIA: estados Pendiente / Activo / Finalizado y fecha de la próxima sesión
ALTER TABLE ASIGNACION_MONITORIA
    MODIFY estado_asignacion ENUM('Pendiente','Activo','Finalizado') NOT NULL DEFAULT 'Pendiente',
    ADD COLUMN proxima_sesion DATE NULL,
    ADD COLUMN inicio_en_vivo DATETIME NULL;

-- 14. HISTORIAL_ASIGNACION: una fila cada vez que el monitor cierra una sesión (guarda las fechas dadas)
CREATE TABLE HISTORIAL_ASIGNACION (
    id_historial INT AUTO_INCREMENT PRIMARY KEY,
    id_asignacion INT NOT NULL,
    fecha_sesion DATE NOT NULL,
    hora_inicio TIME NULL,
    hora_fin TIME NULL,
    resultado ENUM('Continua','Finalizada') NOT NULL,
    fecha_siguiente DATE NULL,
    observaciones TEXT,
    FOREIGN KEY (id_asignacion) REFERENCES ASIGNACION_MONITORIA(id_asignacion) ON DELETE CASCADE
);

-- 15. SOLICITUD_MONITORIA: solicitudes del estudiante que el docente aprueba o rechaza
CREATE TABLE SOLICITUD_MONITORIA (
    id_solicitud INT AUTO_INCREMENT PRIMARY KEY,
    id_estudiante INT NOT NULL,
    id_docente INT NOT NULL,
    materia VARCHAR(100) NOT NULL,
    tipo_apoyo VARCHAR(100),
    fecha_preferida DATE,
    horario VARCHAR(20),
    modalidad ENUM('Presencial','Virtual'),
    detalle TEXT,
    estado ENUM('Pendiente','Aprobada','Rechazada') NOT NULL DEFAULT 'Pendiente',
    motivo_rechazo TEXT NULL,
    id_asignacion INT NULL,          -- se llena al aprobar
    FOREIGN KEY (id_estudiante) REFERENCES ESTUDIANTE(id_usuario),
    FOREIGN KEY (id_docente) REFERENCES PROFESOR(id_usuario),
    FOREIGN KEY (id_asignacion) REFERENCES ASIGNACION_MONITORIA(id_asignacion)
);

-- "Estudiantes en tutoría" de un monitor = asignaciones con estado Pendiente o Activo:
-- SELECT id_monitor, COUNT(*) FROM ASIGNACION_MONITORIA WHERE estado_asignacion <> 'Finalizado' GROUP BY id_monitor;
