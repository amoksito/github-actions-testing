import datetime
import os

# Nombre del archivo de registro donde guardaremos la salida
LOG_FILE = "ejecuciones_log.txt"

# Obtenemos la hora actual en UTC
current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# El mensaje que vamos a loguear
log_message = f"[{current_time}] Script ejecutado exitosamente por GitHub Actions.\n"

# Escribir (Append) el mensaje en el archivo de registro
with open(LOG_FILE, "a") as f:
    f.write(log_message)

print(f"Log creado: {LOG_FILE}. El contenido se guardó.")
