# Sistema de Monitorías Académicas (UCC)

## Cómo abrirlo
- Abre `index.html` (redirige al login), o ejecuta `python -m http.server` en esta carpeta y entra a `http://localhost:8000`.
- Usuarios de prueba (la contraseña es igual al usuario): `estudiante`, `monitor`, `admin`, `docente`.

## Qué funciona
| Rol | Funciones |
|---|---|
| Login | Ingreso por rol, mostrar/ocultar contraseña, recuperación de contraseña (simulada) |
| Estudiante | Solicitar monitoría, ver el estado de sus solicitudes (Pendiente / Aprobada / Rechazada con motivo), «Mis Monitorías» con el **correo del monitor**, mensajería con búsqueda por nombre o correo |
| Monitor | «Ver asignaciones» solo con estados **Activo** y **Finalizado**; **monitoría en tiempo real** en Inicio (activar, terminar sesión, finalizar); sesiones, calendario, CSV; mensajería con búsqueda por nombre o correo |
| Docente | **Solicitudes** de estudiantes (aprobar eligiendo monitor / rechazar con motivo); «Estudiantes en tutoría» sube al aprobar y baja cuando la monitoría termina; seguimiento, alertas, reportes; mensajería con búsqueda por nombre o correo |
| Admin / Jefe de Bienestar | **Super administrador**: cambia usuarios entre Estudiante y Monitor (el rol Docente no se modifica); **inactiva** en vez de eliminar (se conserva el registro y se puede reactivar); Asignaciones con estado en vivo, próxima fecha e **historial de fechas** |

### Ciclo de una monitoría
1. El estudiante envía la solicitud (**Pendiente**).
2. El docente la aprueba y elige monitor → la asignación queda **Pendiente** y «estudiantes en tutoría» sube (+1).
3. El monitor pulsa **Activar ahora** → pasa a **Activo**.
4. Al terminar la sesión del día, el monitor elige:
   - *Continúa otro día* → vuelve a **Pendiente** con la fecha de la próxima sesión; la fecha dada queda en el historial.
   - *Finalizar por completo* → pasa a **Finalizado** y «estudiantes en tutoría» baja (−1).
5. El admin ve todo el recorrido en «Asignaciones» (botón **Historial**).

La mensajería es compartida entre roles: lo que escribe el docente aparece en la bandeja del monitor o estudiante.

## Datos
Todo se guarda en `localStorage` (prefijo `monitorias:`) mediante `js/comun.js`. Para conectar Flask/MySQL basta reemplazar las funciones `Monitorias.leer/guardar` por llamadas a la API; el esquema está en `schema.sql`.
Para reiniciar los datos de prueba: `localStorage.clear()` en la consola del navegador.
