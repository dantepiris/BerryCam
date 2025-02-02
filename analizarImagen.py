import cv2
import numpy as np
import mysql.connector
from datetime import datetime

# Configuración de la conexión a la base de datos
db_config = {
    "host": "mattprofe.com.ar",
    "user": "admin_berryCam",  # Reemplaza con tu usuario de MySQL
    "password": "teamordido",  # Reemplaza con tu contraseña de MySQL
    "database": "berryCam"  # Reemplaza con tu base de datos
}

# Intentar conectarse a la base de datos
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    print("Conexión a la base de datos exitosa")
except mysql.connector.Error as err:
    print(f"Error al conectar a la base de datos: {err}")
    exit()

# Inicializar la cámara (0 o 1 dependiendo de la cámara predeterminada)
cap = cv2.VideoCapture(2)

# Verificar si la cámara está abierta correctamente
if not cap.isOpened():
    print("No se puede abrir la cámara")
    exit()

# Inicializar el factor de conversión como None (aún no calibrado)
factor_conversion = None
real_diameter = 0  # Para almacenar el diámetro real ingresado por el usuario
calibrating = False  # Variable para controlar si estamos en modo de calibración

# Función para capturar la entrada de la calibración
def calibrar_circulo(diametro_real, diametro_pixeles):
    global factor_conversion
    factor_conversion = diametro_real / diametro_pixeles 
    print(f"Factor de conversión calculado: {factor_conversion:.4f} píxeles/mm")
    return factor_conversion

# Función para insertar datos en la base de datos (cantidad de círculos y fecha)
def insertar_datos(cantidad):
    fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Obtener la fecha y hora actual
    try:
        query = """
        INSERT INTO tapitas__datos (cantidad, fechayhora)
        VALUES (%s, %s)
        """
        cursor.execute(query, (cantidad, fecha_hora))
        conn.commit()
        print(f"Datos insertados: cantidad: {cantidad} tapas")
    except mysql.connector.Error as err:
        print(f"Error al insertar los datos: {err}")

# Función para detectar círculos en una imagen
def detectar_circulos_imagen(imagen):
    # Convertir la imagen a escala de grises
    gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    # Aplicar un desenfoque Gaussiano para reducir el ruido
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    # Detectar los círculos utilizando la transformada de Hough
    circles = cv2.HoughCircles(
        blurred, 
        cv2.HOUGH_GRADIENT, dp=1.2, minDist=30, param1=50, param2=30, minRadius=10, maxRadius=100
    )
    cantidad_circulos = 0  # Inicializar el contador de círculos detectados
    # Si se detectan círculos
    if circles is not None:
        # Convertir las coordenadas de los círculos a enteros
        circles = np.round(circles[0, :]).astype("int")
        # Dibujar los círculos detectados
        for (x, y, r) in circles:
            # Dibujar el círculo exterior (contorno)
            cv2.circle(imagen, (x, y), r, (0, 255, 0), 4)
            # Dibujar el centro del círculo
            cv2.circle(imagen, (x, y), 3, (0, 0, 255), 3)
            # Contabilizar este círculo
            cantidad_circulos += 1
    return cantidad_circulos, imagen

# Bucle principal
while True:
    # Capturar un cuadro (frame) desde la cámara
    ret, frame = cap.read()
    
    if not ret:
        print("No se puede recibir el cuadro (frame)")
        break

    # Mostrar la imagen con los círculos detectados en tiempo real
    cv2.imshow("Círculos Detectados", frame)

    # Detectar la tecla presionada para acciones adicionales
    key = cv2.waitKey(1) & 0xFF

    # Salir con la tecla 'q'
    if key == ord('q'):
        break

    # Iniciar proceso de calibración con la tecla 'c'
    if key == ord('c') and not calibrating:
        print("Por favor, ingrese el diámetro real del círculo de referencia en milímetros")
        calibrating = True
        # Pedir al usuario que ingrese el diámetro real (puedes ajustarlo según tu necesidad)
        real_diameter = float(input("Introduce el diámetro real del círculo (en mm): "))
        print(f"Diámetro real del círculo: {real_diameter} mm")
        print("Asegúrate de que el círculo de referencia esté bien visible en la cámara.")
        print("Cuando lo tengas, presiona la tecla 'Enter' para calibrar.")
        
        # Se espera un segundo cuadro para capturar el diámetro en píxeles
        while True:
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (15, 15), 0)
            circles = cv2.HoughCircles(
                blurred, 
                cv2.HOUGH_GRADIENT, dp=1.2, minDist=30, param1=50, param2=30, minRadius=10, maxRadius=100
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                for (x, y, r) in circles:
                    # Dibujar el círculo de referencia
                    cv2.circle(frame, (x, y), r, (0, 255, 0), 4)
                    cv2.circle(frame, (x, y), 3, (0, 0, 255), 3)

                    # Calcular el diámetro en píxeles
                    diametro_pixeles = 2 * r
                    # Realizar la calibración
                    factor_conversion = calibrar_circulo(real_diameter, diametro_pixeles)
                    calibrating = False
                    break  # Salir del bucle de calibración

            cv2.imshow("Calibración - Círculo de referencia", frame)
            if cv2.waitKey(1) & 0xFF == ord('\r'):  # Enter para finalizar calibración
                break

    # Capturar una foto al presionar la tecla 'f'
    if key == ord('f'):
        # Obtener la fecha y hora actual para nombrar la foto
        filename = datetime.now().strftime("foto_%Y%m%d_%H%M%S.jpg")
        # Guardar la imagen en un archivo
        cv2.imwrite(filename, frame)
        print(f"Foto guardada como {filename}")

        # Ahora, leer la imagen y detectar los círculos en ella
        foto = cv2.imread(filename)
        cantidad_circulos, imagen_con_circulos = detectar_circulos_imagen(foto)

        # Mostrar la imagen con los círculos detectados
        cv2.imshow("Círculos Detectados en la Foto", imagen_con_circulos)
        
        # Insertar la cantidad de círculos en la base de datos
        if cantidad_circulos > 0:
            insertar_datos(cantidad_circulos)
        print(f"Se detectaron {cantidad_circulos} círculos en la foto.")

# Liberar la cámara, cerrar las ventanas y desconectar la base de datos
cap.release()
cv2.destroyAllWindows()
cursor.close()
conn.close()