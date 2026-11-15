import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Abre una conexión MySQL usando variables de entorno."""
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "@Luiferpt12."),
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
