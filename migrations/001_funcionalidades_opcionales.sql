-- Ejecutar SOLO si desea habilitar solicitudes e historial persistente.
-- No crea ni elimina la base de datos; trabaja sobre la base existente seleccionada en Workbench.
-- Haga un respaldo antes de ejecutar.

CREATE TABLE IF NOT EXISTS solicitud_monitoria (
  id_solicitud INT NOT NULL AUTO_INCREMENT,
  id_estudiante INT NOT NULL,
  id_docente INT NOT NULL,
  materia VARCHAR(100) NOT NULL,
  tipo_apoyo VARCHAR(100) NULL,
  fecha_preferida DATE NULL,
  horario VARCHAR(40) NULL,
  modalidad ENUM('Presencial','Virtual') NOT NULL DEFAULT 'Presencial',
  detalle TEXT NULL,
  estado ENUM('Pendiente','Aprobada','Rechazada') NOT NULL DEFAULT 'Pendiente',
  motivo_rechazo TEXT NULL,
  id_asignacion INT NULL,
  fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_solicitud),
  KEY idx_solicitud_estudiante (id_estudiante),
  KEY idx_solicitud_docente (id_docente),
  CONSTRAINT fk_solicitud_estudiante FOREIGN KEY (id_estudiante) REFERENCES estudiante(id_usuario),
  CONSTRAINT fk_solicitud_docente FOREIGN KEY (id_docente) REFERENCES profesor(id_usuario),
  CONSTRAINT fk_solicitud_asignacion FOREIGN KEY (id_asignacion) REFERENCES asignacion_monitoria(id_asignacion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS historial_asignacion (
  id_historial INT NOT NULL AUTO_INCREMENT,
  id_asignacion INT NOT NULL,
  fecha_sesion DATE NOT NULL,
  hora_inicio TIME NULL,
  hora_fin TIME NULL,
  resultado ENUM('Continua','Finalizada') NOT NULL DEFAULT 'Continua',
  fecha_siguiente DATE NULL,
  observaciones TEXT NULL,
  PRIMARY KEY (id_historial),
  KEY idx_historial_asignacion (id_asignacion),
  CONSTRAINT fk_historial_asignacion FOREIGN KEY (id_asignacion) REFERENCES asignacion_monitoria(id_asignacion) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
