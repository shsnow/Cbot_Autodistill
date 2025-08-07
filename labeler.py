import os
import cv2
from autodistill_grounded_sam import GroundedSAM
from autodistill.detection import CaptionOntology
from autodistill_yolov8 import YOLOv8

# --- 1. Configuración Inicial ---
VIDEO_PATH = "videos/C05_CRUCE_COLON_BAJO_PIM_CRR_20250627-073209.mp4"
INPUT_IMAGE_DIR = "imagenes_extraidas"
OUTPUT_DATASET_DIR = "dataset_etiquetado"

# Crear directorios si no existen
os.makedirs(INPUT_IMAGE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DATASET_DIR, exist_ok=True)

# --- 2. Extracción de Fotogramas del Video ---
print("Extrayendo fotogramas del video...")
cap = cv2.VideoCapture(VIDEO_PATH)
frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    # Guardar un fotograma cada segundo (puedes ajustar este valor)
    if frame_count % int(cap.get(cv2.CAP_PROP_FPS)) == 0:
        cv2.imwrite(os.path.join(INPUT_IMAGE_DIR, f"frame_{frame_count}.jpg"), frame)
    frame_count += 1
cap.release()
print(f"Se extrajeron {len(os.listdir(INPUT_IMAGE_DIR))} fotogramas.")

# --- 3. Definición de la Ontología ---
# Aquí defines qué objetos quieres detectar y cómo se llamarán las clases.
# El formato es { "lo que el modelo base debe buscar": "el nombre de tu clase" }
# Por ejemplo, si quieres detectar personas y autos:
ontology = CaptionOntology({
    "camión, excavadora, grúa": "heavy_machine",
     "automovil, camioneta": "light_machine",
    "autobus, microbus, bus de acercamiento, Bus, van":"Bus" ,
})

# --- 4. Etiquetado Automático con el Modelo Base ---
print("Iniciando el etiquetado automático...")
# Usaremos GroundedSAM como nuestro modelo base
base_model = GroundedSAM(ontology=ontology)

# Etiquetar la carpeta de imágenes extraídas
# Esto creará un nuevo directorio con las imágenes y sus archivos de etiquetas en formato YOLO
base_model.label(
    input_folder=INPUT_IMAGE_DIR,
    output_folder=OUTPUT_DATASET_DIR
)
print("Etiquetado automático completado.")
print(f"Los datos etiquetados se han guardado en: {OUTPUT_DATASET_DIR}")


# --- 5. Entrenamiento del Modelo Objetivo ---
print("Iniciando el entrenamiento del modelo objetivo...")
# Usaremos YOLOv8 como nuestro modelo objetivo.
# "yolov8n.pt" es la versión más pequeña y rápida de YOLOv8.
target_model = YOLOv8("yolov8n.pt")

# Entrenar el modelo con los datos que acabamos de etiquetar.
# Autodistill crea un archivo data.yaml dentro del directorio de salida,
# que es lo que necesitamos para el entrenamiento.
target_model.train(
    os.path.join(OUTPUT_DATASET_DIR, "data.yaml"),
    epochs=50 # Puedes ajustar el número de épocas
)

print("¡Entrenamiento completado!")
# El modelo entrenado se guardará en la carpeta 'runs/detect/train'
# (o similar, dependiendo de la versión de ultralytics)