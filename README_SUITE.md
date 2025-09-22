# 🚀 AutoDistill Suite - Plataforma Completa de Etiquetado Automático

Una aplicación web moderna y completa para automatizar y corregir el etiquetado de datasets de detección de objetos.

## ✨ Características Principales

### 🏠 Dashboard Central
- **Navegación intuitiva** entre todas las herramientas
- **Estadísticas** en tiempo real de tus proyectos
- **Flujo de trabajo** guiado paso a paso
- **Tema oscuro moderno** con animaciones suaves

### 🏷️ Herramienta de Etiquetado (Estilo CVAT)
- **Edición interactiva** de bounding boxes
- **Navegación con teclado** (F=siguiente, D=anterior)
- **Guardado automático** al editar
- **Múltiples formatos** de visualización
- **Validación** de anotaciones YOLO

### 🤖 Motor AutoDistill
- **Múltiples modelos** base disponibles (CLIP, OWL-ViT, Grounded-SAM)
- **Configuración avanzada** de parámetros
- **Monitoreo en tiempo real** del progreso
- **Procesamiento por lotes** de imágenes y videos
- **Gestión de clases** personalizable

### 📁 Gestión de Archivos
- **Explorador integrado** de carpetas y archivos
- **Soporte para videos** (extracción automática de frames)
- **Organización de proyectos** y datasets
- **Conversión automática** a formato YOLO
- **Validación** de estructura de datasets

### ⚙️ Procesamiento de Videos
- **Extracción inteligente** de frames
- **Configuración de intervalos** personalizables
- **Vista previa** de videos
- **Múltiples formatos** soportados
- **Procesamiento por lotes**

## 🏗️ Arquitectura

```
📁 AutoDistill Suite/
├── 📄 main_app.py              # Aplicación principal con navegación
├── 📁 components/              # Componentes modulares
│   ├── 🏷️ annotation_tool.py   # Herramienta de etiquetado CVAT
│   ├── 🤖 autodistill_tool.py  # Interface para AutoDistill
│   └── 📁 file_manager.py      # Gestor de archivos y proyectos
├── 📁 utils/                   # Utilidades y lógica de negocio
│   ├── ⚙️ config.py           # Configuración global
│   ├── 🎥 video_processor.py   # Procesamiento de videos
│   └── 📊 dataset_manager.py   # Gestión de datasets
└── 📁 assets/                  # CSS y recursos estáticos
    └── 🎨 custom.css          # Estilos personalizados
```

## 🚀 Instalación y Uso

### 1️⃣ Requisitos
```bash
pip install dash dash-bootstrap-components plotly pillow opencv-python numpy
```

### 2️⃣ Ejecutar la Aplicación
```bash
python main_app.py
```

### 3️⃣ Acceder
Abre tu navegador en: **http://127.0.0.1:8050**

## 📖 Flujo de Trabajo Recomendado

### Paso 1: 📁 Organizar Material
- Ve a **Gestión de Archivos**
- Selecciona tus videos o carpetas de imágenes
- Crea un proyecto nuevo

### Paso 2: 🤖 Generar Anotaciones
- Ve a **AutoDistill Engine**
- Selecciona un modelo base (recomendado: CLIP para empezar)
- Configura las clases a detectar
- Ejecuta el procesamiento automático

### Paso 3: 🏷️ Revisar y Corregir
- Ve a **Herramienta de Etiquetado**
- Revisa las anotaciones generadas
- Edita, elimina o agrega bounding boxes según necesites
- Usa atajos de teclado para navegación rápida

### Paso 4: 📦 Dataset Listo
- Tu dataset estará en formato YOLO
- Listo para entrenar modelos de detección

## ⌨️ Atajos de Teclado

### En la Herramienta de Etiquetado:
- **F** → Siguiente imagen
- **D** → Imagen anterior
- **Arrastrar mouse** → Crear nueva anotación
- **Clic en caja** → Editar anotación existente

## 🎨 Personalización

### Temas y Colores
- El tema principal usa **CYBORG** de Bootstrap
- Color primario: **#00d4aa** (verde azulado)
- Personaliza en `assets/custom.css`

### Modelos AutoDistill
- **CLIP**: Rápido, fácil instalación
- **OWL-ViT**: Balance velocidad/precisión  
- **Grounded-SAM**: Máxima precisión, más recursos

## 🔧 Configuración Avanzada

### Clases Personalizadas
Edita la lista de clases en `utils/config.py`:
```python
DEFAULT_CLASSES = ["vehículo", "persona", "bicicleta"]
```

### Formatos Soportados
- **Imágenes**: JPG, PNG, BMP, TIFF
- **Videos**: MP4, AVI, MOV, MKV, FLV, WMV

## 📊 Características Técnicas

- **Framework**: Dash + Plotly
- **UI**: Bootstrap (tema CYBORG)
- **Procesamiento**: OpenCV + NumPy
- **Formato**: YOLO (compatible con YOLOv8/v9)
- **Multiplataforma**: Windows, Linux, macOS

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Crea un Pull Request

## 📝 Notas de Desarrollo

### Componentes Modulares
Cada herramienta está implementada como un componente independiente que puede ser reutilizado o modificado sin afectar el resto de la aplicación.

### Escalabilidad
La arquitectura permite agregar fácilmente:
- Nuevos modelos de AutoDistill
- Formatos de datos adicionales  
- Herramientas de análisis
- Integraciones con APIs externas

---

**🎯 AutoDistill Suite - Acelera la creación de datasets de IA de forma profesional**