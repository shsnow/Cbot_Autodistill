# 🔧 Herramienta de Corrección de Etiquetado - Similar a CVAT

Esta herramienta te permite corregir y editar las etiquetas generadas por autodistill de manera visual e interactiva, similar a CVAT pero corriendo localmente.

## 📁 Archivos Creados

- `advanced_annotation_tool.py` - Herramienta principal con Dash (más completa)
- `gradio_annotation_tool.py` - Herramienta alternativa con Gradio (más simple)
- `requirements_annotation_tool.txt` - Dependencias para Dash
- `requirements_gradio.txt` - Dependencias para Gradio
- `instalar_y_ejecutar.bat` - Script para instalar y ejecutar Dash
- `instalar_gradio.bat` - Script para instalar y ejecutar Gradio

## 🚀 Instalación y Uso

### Opción 1: Herramienta Avanzada con Dash (Recomendada)

1. **Instalación automática:**
   ```batch
   # Ejecutar el archivo batch
   instalar_y_ejecutar.bat
   ```

2. **Instalación manual:**
   ```batch
   pip install -r requirements_annotation_tool.txt
   python advanced_annotation_tool.py
   ```

3. **Abrir en navegador:**
   - Ve a: `http://localhost:8050`

### Opción 2: Herramienta Simple con Gradio

1. **Instalación automática:**
   ```batch
   # Ejecutar el archivo batch
   instalar_gradio.bat
   ```

2. **Instalación manual:**
   ```batch
   pip install -r requirements_gradio.txt
   python gradio_annotation_tool.py
   ```

## 🎯 Características Principales

### Herramienta Dash (Avanzada)
- ✅ Visualización interactiva de imágenes y bounding boxes
- ✅ Dibujo directo de nuevos bounding boxes con el mouse
- ✅ Edición visual de bounding boxes existentes
- ✅ Navegación fluida entre imágenes
- ✅ Lista lateral con todas las anotaciones
- ✅ Eliminación de anotaciones individuales
- ✅ Eliminación de frames completos
- ✅ Guardado automático de cambios
- ✅ Estadísticas en tiempo real
- ✅ Ajuste de opacidad y opciones de visualización
- ✅ Notificaciones toast para feedback

### Herramienta Gradio (Simple)
- ✅ Interfaz simple y fácil de usar
- ✅ Visualización de imágenes con anotaciones
- ✅ Navegación entre imágenes
- ✅ Agregar anotaciones manualmente (coordenadas)
- ✅ Eliminar anotaciones por ID
- ✅ Guardar cambios
- ✅ Eliminar frames

## 📋 Instrucciones de Uso

### Navegación
- **Anterior/Siguiente**: Navega entre las imágenes
- **Primero/Último**: Ve directamente a la primera/última imagen

### Editar Anotaciones (Dash)
1. **Crear nueva caja**: 
   - Selecciona la clase en el sidebar
   - Dibuja un rectángulo directamente en la imagen
   - La caja se creará automáticamente

2. **Editar caja existente**:
   - Haz clic en los botones de la lista de anotaciones
   - Usa las herramientas de edición

3. **Eliminar caja**:
   - Usa el botón 🗑️ en la lista de anotaciones

### Editar Anotaciones (Gradio)
1. **Crear nueva caja**:
   - Ingresa las coordenadas X Min, Y Min, X Max, Y Max
   - Selecciona la clase
   - Haz clic en "Agregar Caja"

2. **Eliminar caja**:
   - Ingresa el ID de la anotación a eliminar
   - Haz clic en "Eliminar"

### Guardar Cambios
- **Dash**: Botón "💾 Guardar" (o auto-guardado)
- **Gradio**: Botón "💾 Guardar"

### Eliminar Frames
- Usa el botón "🗑️ Eliminar Frame" para eliminar la imagen actual y sus anotaciones

## 📊 Formato de Datos

La herramienta trabaja con el formato YOLO estándar:
```
clase_id x_centro y_centro ancho alto
```

Donde todos los valores están normalizados (0.0 - 1.0).

## 🔧 Configuración

### Cambiar Directorio del Dataset
Modifica la línea en el código:
```python
tool = AdvancedAnnotationTool(dataset_path="tu_directorio_aqui")
```

### Agregar Más Clases
Modifica la lista en el código:
```python
self.classes = ["vehículo", "persona", "bicicleta", ...]
```

## ⚠️ Requisitos del Sistema

- Python 3.7+
- Windows (los scripts .bat son para Windows)
- Navegador web moderno

## 📁 Estructura de Directorios Esperada

```
dataset_cruce_3/
├── train/
│   ├── images/
│   │   ├── frame_0.jpg
│   │   ├── frame_15.jpg
│   │   └── ...
│   └── labels/
│       ├── frame_0.txt
│       ├── frame_15.txt
│       └── ...
└── data.yaml
```

## 🐛 Solución de Problemas

### Error: "Directorio no encontrado"
- Asegúrate de que existe el directorio `dataset_cruce_3/train/images/`
- Verifica que hay imágenes (.jpg, .jpeg, .png) en el directorio

### Error: "No se pudo resolver la importación"
- Ejecuta los scripts de instalación (.bat)
- O instala manualmente: `pip install -r requirements_*.txt`

### La aplicación no se abre
- Verifica que no hay otro proceso usando el puerto 8050 o 7860
- Intenta con otro puerto modificando el código

### Las anotaciones no se guardan
- Verifica permisos de escritura en el directorio de etiquetas
- Asegúrate de hacer clic en "Guardar"

## 💡 Consejos de Uso

1. **Guarda frecuentemente**: Usa el botón de guardar regularmente
2. **Revisa las estadísticas**: Usa el panel de estadísticas para verificar tu progreso
3. **Ajusta la opacidad**: Modifica la opacidad de las cajas para mejor visualización
4. **Usa atajos de teclado**: Los navegadores soportan navegación con flechas
5. **Verifica coordenadas**: Asegúrate de que las cajas están bien posicionadas

## 📞 Soporte

Si encuentras problemas:
1. Verifica que seguiste todos los pasos de instalación
2. Revisa que la estructura de directorios es correcta
3. Comprueba que las dependencias están instaladas

¡Disfruta editando tus anotaciones! 🎉
