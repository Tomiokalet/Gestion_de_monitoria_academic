
from db import get_connection

conexion = get_connection()

if conexion:
    try:
        cursor = conexion.cursor()

        # Comprobar la conexión y consultar la base de datos actual
        cursor.execute("SELECT DATABASE()")
        resultado = cursor.fetchone()

        print("Base de datos conectada:", resultado[0])

        # Comprobar que existe la tabla usuario
        cursor.execute("SHOW TABLES LIKE 'usuario'")
        tabla = cursor.fetchone()

        if tabla:
            print("La tabla usuario existe.")
        else:
            print("No se encontró la tabla usuario.")

        cursor.close()

    finally:
        conexion.close()
        print("Conexión cerrada correctamente.")
else:
    print("No se pudo establecer la conexión.")
