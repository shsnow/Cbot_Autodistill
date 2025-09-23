# 🔧 Advanced Annotation Tool - Herramienta Avanzada de Etiquetado YOLO

> Una herramienta web interactiva similar a CVAT para crear, editar y corregir anotaciones YOLO con facilidad.

## 📋 Tabla de Contenido

- [🔧 Advanced Annotation Tool - Herramienta Avanzada de Etiquetado YOLO](#-advanced-annotation-tool---herramienta-avanzada-de-etiquetado-yolo)
  - [📋 Tabla de Contenido](#-tabla-de-contenido)
  - [🎯 Descripción General](#-descripción-general)
  - [✨ Características Principales](#-características-principales)
  - [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema)
    - [📁 Estructura de Directorios](#-estructura-de-directorios)
    - [🔧 Componentes Modulares](#-componentes-modulares)
  - [⚙️ Instalación y Configuración](#️-instalación-y-configuración)
    - [📦 Requisitos](#-requisitos)
    - [🚀 Instalación](#-instalación)
    - [📂 Estructura de Dataset](#-estructura-de-dataset)
  - [🎮 Guía de Uso](#-guía-de-uso)
    - [🚀 Ejecución Básica](#-ejecución-básica)
    - [🖱️ Controles de la Interfaz](#️-controles-de-la-interfaz)
    - [⌨️ Atajos de Teclado](#️-atajos-de-teclado)
  - [📐 Funcionalidades Detalladas](#-funcionalidades-detalladas)
    - [🎨 Creación de Anotaciones](#-creación-de-anotaciones)
    - [✏️ Edición de Anotaciones](#️-edición-de-anotaciones)
    - [🎯 Selección y Cambio de Clases](#-selección-y-cambio-de-clases)
    - [🗑️ Eliminación de Anotaciones](#️-eliminación-de-anotaciones)
    - [↶ Sistema de Deshacer](#-sistema-de-deshacer)
  - [⚙️ Configuración Avanzada](#️-configuración-avanzada)
    - [📋 Archivo data.yaml](#-archivo-datayaml)
    - [🎨 Personalización de Colores](#-personalización-de-colores)
  - [🔧 Arquitectura Técnica](#-arquitectura-técnica)
    - [📊 Componentes de la Aplicación](#-componentes-de-la-aplicación)
    - [🔄 Flujo de Datos](#-flujo-de-datos)
    - [💾 Sistema de Persistencia](#-sistema-de-persistencia)
  - [🎨 Personalización de Diseño](#-personalización-de-diseño)
    - [🖌️ Temas y Estilos](#️-temas-y-estilos)
    - [📱 Componentes de UI](#-componentes-de-ui)
  - [🐛 Solución de Problemas](#-solución-de-problemas)
  - [🔮 Roadmap de Mejoras](#-roadmap-de-mejoras)
  - [📄 Licencia](#-licencia)

## 🎯 Descripción General

La **Advanced Annotation Tool** es una aplicación web desarrollada en Python con **Dash** y **Plotly** que permite crear, editar y corregir anotaciones en formato YOLO de manera visual e interactiva. Está diseñada como una alternativa más ligera y especializada a herramientas como CVAT.

### 🌟 ¿Por qué esta herramienta?

- **Interfaz amigable**: Web-based, no requiere instalación de software pesado
- **Especializada en YOLO**: Optimizada específicamente para el formato YOLO v8/v5
- **Edición interactiva**: Arrastra y redimensiona bounding boxes visualmente
- **Guardado automático**: No pierdes tu trabajo nunca
- **Sistema de deshacer**: Ctrl+Z funcional para todas las acciones
- **Navegación fluida**: Atajos de teclado para navegar rápidamente

## ✨ Características Principales

### 🎨 **Creación y Edición Visual**
- ✏️ Dibuja bounding boxes arrastrando el mouse
- 🔄 Redimensiona arrastrando bordes y esquinas
- 🎯 Selecciona anotaciones con un clic
- 🏷️ Cambia clases fácilmente
- 🎨 Colores personalizados por clase

### 🚀 **Navegación Inteligente**
- ⏩ Navegación con teclas F/D (siguiente/anterior)
- 🔢 Salto directo a primera/última imagen
- 📊 Contador visual del progreso
- 🔍 Información detallada de cada anotación

### 💾 **Gestión de Datos**
- 💾 Guardado automático en formato YOLO
- ↶ Sistema de deshacer (Ctrl+Z) hasta 20 acciones
- 📋 Validación automática de coordenadas
- 🔄 Recarga de datos en tiempo real

### 🗑️ **Eliminación Flexible**
- 🎯 Eliminar anotación seleccionada (Supr)
- 🗑️ Eliminar última anotación creada
- 🔢 Eliminar por ID específico
- 🚨 Eliminar todo el frame (con confirmación)

### 📊 **Información y Estadísticas**
- 📈 Estadísticas por clase en tiempo real
- 📏 Información de coordenadas y tamaños
- 🏷️ Lista visual de todas las anotaciones
- 📋 Contadores y progreso visual

## 🏗️ Arquitectura del Sistema

### 📁 Estructura de Directorios

```
Cbot_Autodistill/
├── advanced_annotation_tool_modular.py  # 🎯 Aplicación principal
├── utils/                               # 📦 Módulos utilitarios
│   ├── __init__.py                     # 📋 Exports del paquete
│   ├── annotation_manager.py           # 💾 Gestión de archivos YOLO
│   ├── callback_manager.py             # 🔄 Lógica de callbacks Dash
│   ├── config_loader.py                # ⚙️ Carga de configuración YAML
│   ├── coordinate_converter.py         # 📐 Conversiones YOLO ↔ Píxeles
│   ├── figure_generator.py             # 🖼️ Generación de figuras Plotly
│   └── undo_manager.py                 # ↶ Sistema de deshacer
├── dataset_cruce_3/                    # 📂 Dataset de ejemplo
│   ├── data.yaml                      # ⚙️ Configuración del dataset
│   ├── images/                        # 🖼️ Imágenes del dataset
│   └── annotations/                   # 🏷️ Anotaciones YOLO
├── requirements.txt                    # 📦 Dependencias Python
└── README.md                          # 📖 Documentación
```

### 🔧 Componentes Modulares

#### 🎯 **AdvancedAnnotationTool** (Componente Principal)
```python
class AdvancedAnnotationTool:
    """Herramienta principal que orquesta todos los componentes"""
    
    # Inicialización y configuración
    def __init__(self, dataset_path)
    def _initialize_modules()
    def _validate_directories()
    def _load_image_files()
    
    # Interfaz de usuario
    def setup_layout()
    def setup_callbacks()
    def _create_header()
    def _create_control_panel()
    def _create_main_content()
```

#### 💾 **AnnotationManager** (Gestión de Datos)
```python
class AnnotationManager:
    """Maneja la carga y guardado de anotaciones YOLO"""
    
    def load_annotations(image_filename)     # Cargar desde .txt
    def save_annotations(image_filename)     # Guardar en formato YOLO
    def validate_annotation(annotation)      # Validar rangos y formato
```

#### 📐 **CoordinateConverter** (Conversiones)
```python
class CoordinateConverter:
    """Convierte entre coordenadas YOLO y píxeles"""
    
    @staticmethod
    def yolo_to_pixel(annotation, width, height)    # YOLO → Píxeles
    @staticmethod
    def pixel_to_yolo(x1, y1, x2, y2, w, h)       # Píxeles → YOLO
    @staticmethod
    def validate_pixel_coords(coords)               # Validación
```

#### 🖼️ **FigureGenerator** (Visualización)
```python
class FigureGenerator:
    """Genera figuras de Plotly con imágenes y anotaciones"""
    
    def create_figure_with_annotations()     # Crear figura completa
    def _create_shapes()                    # Crear bounding boxes
    def _add_text_annotations()             # Añadir etiquetas de texto
    def _configure_layout()                 # Configurar diseño
```

#### ↶ **UndoManager** (Sistema de Deshacer)
```python
class UndoManager:
    """Sistema de deshacer con stack de estados"""
    
    def push_state(image, annotations)      # Guardar estado
    def pop_state()                        # Recuperar estado
    def can_undo()                         # Verificar disponibilidad
    def get_undo_count()                   # Contar acciones disponibles
```

#### ⚙️ **ConfigLoader** (Configuración)
```python
class ConfigLoader:
    """Carga configuración desde archivos YAML"""
    
    def get_classes()                      # Obtener lista de clases
    def get_colors(num_classes)            # Obtener colores personalizados
    def _load_config()                     # Cargar archivo YAML
```

## ⚙️ Instalación y Configuración

### 📦 Requisitos

- **Python 3.8+**
- **Navegador web moderno** (Chrome, Firefox, Edge)
- **Dependencias Python** (ver requirements.txt)

### 🚀 Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd Cbot_Autodistill
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Verificar estructura de datos**
```bash
# Tu dataset debe tener esta estructura:
dataset_name/
├── data.yaml          # Configuración de clases
├── images/            # Archivos de imagen (.jpg, .png, .jpeg)
└── annotations/       # Archivos YOLO (.txt) - se crea automáticamente
```

### 📂 Estructura de Dataset

**Ejemplo de `data.yaml`:**
```yaml
# Configuración de clases
names:
  0: sign
  1: heavy_machine
  2: light_machine
  3: bus
  4: fork

# Número total de clases
nc: 5

# Rutas del dataset
train: images/
val: images/  # opcional
test: images/ # opcional

# Colores personalizados (opcional)
colors:
  - [0, 212, 170]     # sign - verde azulado
  - [255, 107, 107]   # heavy_machine - rojo suave
  - [78, 205, 196]    # light_machine - turquesa
  - [69, 183, 209]    # bus - azul
  - [254, 202, 87]    # fork - amarillo
```

## 🎮 Guía de Uso

### 🚀 Ejecución Básica

**Ejecutar la aplicación:**
```bash
python advanced_annotation_tool_modular.py
```

**Ejecutar con dataset personalizado:**
```bash
python advanced_annotation_tool_modular.py --dataset mi_dataset/
```

**La aplicación se abrirá en:** `http://127.0.0.1:8050`

### 🖱️ Controles de la Interfaz

#### 📂 **Panel de Navegación**
- **◀◀ Primero**: Ir a la primera imagen
- **◀ Anterior**: Imagen anterior (también tecla `D`)
- **Siguiente ▶**: Siguiente imagen (también tecla `F`)
- **▶▶ Último**: Ir a la última imagen

#### 🛠️ **Panel de Herramientas**
- **↶ Deshacer**: Deshacer última acción (también `Ctrl+Z`)
- **🗑️ Seleccionada**: Eliminar anotación seleccionada (también `Supr`)
- **🗑️ Última**: Eliminar última anotación creada
- **🗑️ ID**: Eliminar anotación por ID específico
- **🗑️ Eliminar Frame**: Eliminar todas las anotaciones de la imagen

#### 🎨 **Panel de Configuración**
- **Clase para nuevas anotaciones**: Selector de clase por defecto
- **🎯 CAMBIAR CLASE**: Sección para cambiar clase de anotación seleccionada
- **Opacidad de las cajas**: Control deslizante (0.1 - 1.0)
- **☑️ Mostrar IDs**: Mostrar/ocultar IDs de anotaciones
- **☑️ Mostrar coordenadas**: Mostrar/ocultar coordenadas YOLO

#### 🏷️ **Lista de Anotaciones**
- **🎯 Botón**: Seleccionar anotación para editar clase
- **🗑️ Botón**: Eliminar anotación específica
- **Información**: Coordenadas y tamaño de cada anotación

### ⌨️ Atajos de Teclado

| Tecla | Acción |
|-------|--------|
| `F` | Siguiente imagen |
| `D` | Imagen anterior |
| `Ctrl+Z` | Deshacer última acción |
| `Supr` / `Delete` | Eliminar anotación seleccionada |

## 📐 Funcionalidades Detalladas

### 🎨 Creación de Anotaciones

1. **Seleccionar clase**: Usar el selector "Clase para nuevas anotaciones"
2. **Dibujar bounding box**: 
   - Hacer clic y arrastrar en la imagen
   - La caja se crea automáticamente al soltar
3. **Guardado automático**: La anotación se guarda inmediatamente

**Formato YOLO generado:**
```
class_id x_center y_center width height
0 0.500000 0.300000 0.200000 0.150000
```

### ✏️ Edición de Anotaciones

#### 🔄 **Redimensionar**
- Arrastra cualquier **borde** para cambiar ancho/alto
- Arrastra cualquier **esquina** para redimensionar proporcionalmente

#### 🚚 **Mover**
- Arrastra desde el **interior** de la bounding box

#### 💾 **Guardado**
- Los cambios se guardan automáticamente al terminar la edición
- El sistema mantiene un historial para deshacer

### 🎯 Selección y Cambio de Clases

#### 🖱️ **Formas de Seleccionar**

1. **Clic directo**: Hacer clic en cualquier parte de la bounding box
2. **Botón de lista**: Presionar 🎯 en la lista de anotaciones
3. **Edición automática**: Se selecciona automáticamente al editar

#### 🏷️ **Cambio de Clase**

1. **Seleccionar anotación** (cualquier método anterior)
2. **Verificar selección**: La caja se resalta en amarillo
3. **Elegir nueva clase**: En el selector "🔄 Nueva clase"
4. **Aplicar cambio**: Presionar "✅ CAMBIAR AHORA"
5. **Confirmación**: Mensaje de éxito con el cambio realizado

### 🗑️ Eliminación de Anotaciones

#### 🎯 **Eliminar Seleccionada** (`Supr`)
- Selecciona una anotación (clic o botón 🎯)
- Presiona `Supr` o el botón "🗑️ Seleccionada"

#### 🗑️ **Eliminar Última**
- Elimina la anotación creada más recientemente
- Útil para corregir errores rápidamente

#### 🔢 **Eliminar por ID**
- Ingresa el ID en el campo numérico
- Presiona "🗑️ ID"

#### 🚨 **Eliminar Frame Completo**
- Elimina TODAS las anotaciones de la imagen actual
- Requiere confirmación en modal

### ↶ Sistema de Deshacer

#### 🔄 **Funcionalidad**
- Hasta **20 acciones** se pueden deshacer
- Funciona para: crear, editar, eliminar, cambiar clase
- Se mantiene por imagen (cada imagen tiene su historial)

#### ⌨️ **Uso**
- `Ctrl+Z` o botón "↶ Deshacer"
- Restaura el estado anterior exacto
- Mensaje de confirmación con la acción deshecha

## ⚙️ Configuración Avanzada

### 📋 Archivo data.yaml

El archivo `data.yaml` define las clases y configuración del dataset:

#### 🔧 **Formatos Soportados**

**Lista de nombres (Ultralytics):**
```yaml
names: [clase1, clase2, clase3]
nc: 3
```

**Diccionario índice→nombre:**
```yaml
names:
  0: vehiculo
  1: peaton  
  2: ciclista
nc: 3
```

**Diccionario nombre→índice:**
```yaml
names:
  vehiculo: 0
  peaton: 1
  ciclista: 2
nc: 3
```

#### 📂 **Rutas del Dataset**
```yaml
train: images/           # Ruta a imágenes de entrenamiento
val: images/            # Ruta a imágenes de validación (opcional)
test: images/           # Ruta a imágenes de prueba (opcional)
```

### 🎨 Personalización de Colores

#### 🌈 **Colores por Clase**
```yaml
colors:
  - [255, 0, 0]      # Clase 0: Rojo
  - [0, 255, 0]      # Clase 1: Verde  
  - [0, 0, 255]      # Clase 2: Azul
  - [255, 255, 0]    # Clase 3: Amarillo
  - [255, 0, 255]    # Clase 4: Magenta
```

#### 🎨 **Colores por Defecto**
Si no se especifican colores, se usan estos:
- `#00d4aa` - Verde azulado
- `#ff6b6b` - Rojo suave
- `#4ecdc4` - Turquesa
- `#45b7d1` - Azul
- `#feca57` - Amarillo
- `#ff9ff3` - Rosa
- `#54a0ff` - Azul claro
- `#9c88ff` - Púrpura

## 🔧 Arquitectura Técnica

### 📊 Componentes de la Aplicación

#### 🎭 **Frontend (Dash + Plotly)**
```python
# Componentes principales
dbc.Container([
    dcc.Store(),              # Estados de la aplicación
    dbc.Row([                # Panel de control
        dbc.Col([navigation]),
        dbc.Col([tools]),
        dbc.Col([actions])
    ]),
    dbc.Row([                # Contenido principal
        dbc.Col([            # Visor de imagen
            dcc.Graph()      # Plotly con imagen + shapes
        ], width=8),
        dbc.Col([            # Panel lateral
            annotations_list, # Lista de anotaciones
            config_panel,    # Configuración
            statistics       # Estadísticas
        ], width=4)
    ])
])
```

#### 🔄 **Sistema de Callbacks**
```python
# Patrón de callbacks principales
@app.callback(...)
def navigation_callback():     # Navegación entre imágenes
def shape_interaction():       # Edición de bounding boxes  
def annotation_selection():    # Selección de anotaciones
def class_change():           # Cambio de clases
def deletion_callbacks():     # Eliminación de anotaciones
def undo_callback():          # Sistema de deshacer
```

### 🔄 Flujo de Datos

#### 📊 **Estados de la Aplicación (dcc.Store)**
```python
stores = {
    'current-annotations': [],        # Anotaciones de imagen actual
    'current-image-data': {},        # Metadatos de imagen
    'image-dimensions': {},          # Ancho/alto de imagen
    'selected-annotation': None,     # Índice de anotación seleccionada
    'keyboard-trigger': 0            # Trigger para eventos de teclado
}
```

#### 🔄 **Ciclo de Vida de una Anotación**
```
1. Usuario dibuja bounding box
   ↓
2. Plotly genera evento relayoutData
   ↓  
3. CallbackManager.handle_shape_interaction()
   ↓
4. CoordinateConverter.pixel_to_yolo()
   ↓
5. AnnotationManager.save_annotations()
   ↓
6. FigureGenerator.create_figure_with_annotations()
   ↓
7. UI se actualiza con nueva figura
```

### 💾 Sistema de Persistencia

#### 📁 **Formato de Archivos YOLO**
```
imagen.jpg  →  imagen.txt
formato: class_id x_center y_center width height
ejemplo: 0 0.500000 0.300000 0.200000 0.150000
```

#### 🔄 **Guardado Automático**
```python
def save_annotations(self, image_filename, annotations):
    """Guardado inmediato en formato YOLO"""
    if not annotations:
        # Eliminar archivo si no hay anotaciones
        os.remove(label_path)
    else:
        # Escribir todas las anotaciones
        with open(label_path, 'w') as f:
            for ann in annotations:
                line = f"{ann['class_id']} {ann['x_center']:.6f} ..."
                f.write(line)
```

## 🎨 Personalización de Diseño

### 🖌️ Temas y Estilos

#### 🌙 **Tema Oscuro (Cyborg)**
```python
external_stylesheets = [dbc.themes.CYBORG]

# Colores principales
background_primary = '#0a0a0a'      # Negro profundo
background_secondary = '#1a1a1a'    # Gris muy oscuro
background_tertiary = '#2d3748'     # Gris oscuro
accent_primary = '#00d4aa'          # Verde azulado
accent_warning = '#ffd700'          # Amarillo dorado
text_primary = '#ffffff'            # Blanco
text_secondary = '#adb5bd'          # Gris claro
```

#### 🎨 **Gradientes y Efectos**
```python
# Gradientes usados
header_gradient = 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)'
card_gradient = 'linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)'
accent_gradient = 'linear-gradient(135deg, rgba(255,215,0,0.15) 0%, rgba(255,215,0,0.08) 100%)'

# Sombras y efectos
box_shadow = '0 4px 8px rgba(0,212,170,0.1)'
text_shadow = '0 0 10px rgba(0,212,170,0.5)'
```

### 📱 Componentes de UI

#### 🏷️ **Cards de Anotación**
```python
annotation_card = dbc.Card([
    dbc.CardBody([
        # Header con clase y botones
        dbc.Row([
            dbc.Col([
                html.H6("🏷️ clase_name", className="card-title"),
                html.Small("Índice: X", className="text-muted")
            ], width=6),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("🎯", color="warning"),  # Seleccionar
                    dbc.Button("🗑️", color="danger")    # Eliminar
                ])
            ], width=6)
        ]),
        # Información detallada
        html.Small([
            f"Centro: ({x:.3f}, {y:.3f})",
            f"Tamaño: {w:.3f} × {h:.3f}"
        ])
    ])
], style={
    "border-left": f"4px solid {color}",
    "box-shadow": "0 4px 8px rgba(0,212,170,0.1)",
    "background": "#2d3748"
})
```

#### 🎯 **Panel de Cambio de Clase**
```python
class_change_panel = dbc.Alert([
    html.H5("🎯 CAMBIAR CLASE DE ANOTACIÓN SELECCIONADA"),
    dbc.Alert(id="selected-info", color="info"),  # Estado de selección
    dbc.Row([
        dbc.Col([
            html.Label("🔄 Nueva clase:"),
            dbc.Select(id="selected-class-selector")
        ], width=7),
        dbc.Col([
            html.Label("🚀 Acción:"),
            dbc.Button("✅ CAMBIAR AHORA", id="change-class-button")
        ], width=5)
    ])
], color="warning", style={
    "background": "linear-gradient(...)",
    "border": "3px solid #ffd700"
})
```

## 🐛 Solución de Problemas

### ❌ **Problemas Comunes**

#### 🖼️ **"No se encontraron imágenes"**
```bash
# Verificar estructura de directorios
dataset/
├── images/          # ← Debe existir con .jpg/.png/.jpeg
└── annotations/     # ← Se crea automáticamente
```

#### 📄 **"Archivo YAML no encontrado"**
```bash
# Crear data.yaml básico
echo "names: [clase1, clase2]" > data.yaml
echo "nc: 2" >> data.yaml
```

#### 🎨 **"Las anotaciones no se ven"**
- Verificar que el slider de opacidad no esté en 0
- Activar "Mostrar IDs" para ver las etiquetas
- Verificar que hay anotaciones en la imagen actual

#### 💾 **"Los cambios no se guardan"**
- Verificar permisos de escritura en la carpeta `annotations/`
- Revisar la consola para errores de guardado
- Verificar que el formato YOLO sea válido

### 🔧 **Debug y Logs**

La aplicación genera logs detallados:
```python
# Logs importantes a revistar
print("DEBUG: Cambiando a imagen: X")           # Navegación
print("DEBUG: Shape X seleccionada/editada")    # Selección
print("DEBUG: Guardando X anotaciones")         # Guardado
print("ERROR changing class: ...")              # Errores
```

## 🔮 Roadmap de Mejoras

### 🎨 **Mejoras de Diseño (Sin afectar funcionalidad)**

#### 🌈 **Temas Alternativos**
- [ ] Tema claro (Bootstrap/Flatly)
- [ ] Tema de alto contraste
- [ ] Tema personalizable por usuario

#### 📱 **Responsividad**
- [ ] Optimización para tablets
- [ ] Layout adaptativo para pantallas pequeñas
- [ ] Controles táctiles mejorados

#### 🎨 **Componentes Visuales**
- [ ] Animaciones suaves en transiciones
- [ ] Indicadores de progreso más detallados  
- [ ] Tooltips informativos mejorados
- [ ] Icons y iconografía consistente

#### 🖼️ **Visualización Mejorada**
- [ ] Zoom y pan en imágenes grandes
- [ ] Minimap para navegación en imágenes grandes
- [ ] Vista previa de imágenes en navegación
- [ ] Filtros y ajustes de imagen

### 🚀 **Nuevas Funcionalidades**

#### ⚡ **Performance**
- [ ] Carga lazy de imágenes
- [ ] Cache de anotaciones en memoria
- [ ] Navegación predictiva (precarga)

#### 🔧 **Herramientas Adicionales**
- [ ] Herramienta de duplicado de anotaciones
- [ ] Auto-anotación con modelos pre-entrenados
- [ ] Importación desde otros formatos (COCO, Pascal VOC)
- [ ] Exportación a múltiples formatos

#### 👥 **Colaboración**
- [ ] Múltiples usuarios simultáneos
- [ ] Sistema de comentarios en anotaciones
- [ ] Historial de cambios por usuario

## 📄 Licencia

Este proyecto está bajo licencia [MIT](LICENSE). Siéntete libre de usar, modificar y distribuir según los términos de la licencia.

---

**Desarrollado con ❤️ para la comunidad de Computer Vision**

¿Preguntas o sugerencias? Abre un [issue](../../issues) o contribuye al proyecto!
