import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Abre una conexión MySQL usando variables de entorno."""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "monitorias-db-mmelopadilla-a608.i.aivencloud.com"),
            port=int(os.getenv("DB_PORT", "16992")),
            user=os.getenv("DB_USER", "avnadmin"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME", "monitorias"),
            charset="utf8mb4",
            use_unicode=True,
            connection_timeout=8,
        )
    except Error as exc:
        # No se imprimen credenciales en el mensaje de error.
        raise RuntimeError(
            "No fue posible conectar con MySQL. Revisa el servicio, el puerto "
            "y las variables DB_* del archivo .env."
        ) from exc
