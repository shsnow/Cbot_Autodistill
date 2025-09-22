import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import sys
import base64
import json
import yaml
from PIL import Image
import io
import plotly.graph_objects as go
import plotly.express as px

# Configuración de la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://use.fontawesome.com/releases/v6.0.0/css/all.css"
    ],
    assets_folder='assets',
    suppress_callback_exceptions=True  # ✅ Esto resuelve el problema de IDs no encontrados
)

app.title = "AutoDistill Suite"

class AutoDistillSuite:
    def __init__(self, app):
        self.app = app
        self.current_dataset = "CRUCE_COLON_1_class"
        self.current_image_index = 0
        self.classes = {0: "objeto"}  # Clases por defecto
        
    def load_classes_from_yaml(self, yaml_path="classes.yaml"):
        """Cargar clases desde archivo YAML"""
        try:
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    if 'names' in data:
                        return {i: name for i, name in enumerate(data['names'])}
            return {0: "objeto"}  # Fallback
        except Exception:
            return {0: "objeto"}
    
    def get_image_files(self, dataset_path):
        """Obtener lista de archivos de imagen"""
        try:
            files = [f for f in os.listdir(dataset_path) 
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            return sorted(files)
        except:
            return []
    
    def load_yolo_annotations(self, image_name, dataset_path):
        """Cargar anotaciones YOLO para una imagen"""
        try:
            base_name = os.path.splitext(image_name)[0]
            label_path = os.path.join(dataset_path, f"{base_name}.txt")
            
            annotations = []
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    for line_idx, line in enumerate(f):
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            annotations.append({
                                'id': f"ann_{line_idx}",
                                'class_id': class_id,
                                'x_center': x_center,
                                'y_center': y_center,
                                'width': width,
                                'height': height
                            })
            
            return annotations
        except Exception as e:
            print(f"Error cargando anotaciones: {e}")
            return []
    
    def create_annotation_figure(self, image_path, annotations):
        """Crear figura de Plotly con imagen y anotaciones"""
        try:
            # Cargar imagen
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Obtener dimensiones de la imagen
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # Crear figura
            fig = go.Figure()
            
            # Agregar imagen de fondo
            fig.add_layout_image(
                dict(
                    source=f"data:image/jpeg;base64,{image_data}",
                    xref="x", yref="y",
                    x=0, y=img_height,
                    sizex=img_width, sizey=img_height,
                    sizing="stretch", opacity=1, layer="below"
                )
            )
            
            # Agregar bounding boxes
            for ann in annotations:
                # Convertir coordenadas YOLO a píxeles
                x_center_px = ann['x_center'] * img_width
                y_center_px = ann['y_center'] * img_height
                width_px = ann['width'] * img_width
                height_px = ann['height'] * img_height
                
                x0 = x_center_px - width_px / 2
                x1 = x_center_px + width_px / 2
                y0 = y_center_px - height_px / 2
                y1 = y_center_px + height_px / 2
                
                # Convertir Y para que coincida con el sistema de coordenadas de la imagen
                y0 = img_height - y0
                y1 = img_height - y1
                
                class_name = self.classes.get(ann['class_id'], f"Clase {ann['class_id']}")
                color = px.colors.qualitative.Set1[ann['class_id'] % len(px.colors.qualitative.Set1)]
                
                # Agregar rectángulo
                fig.add_shape(
                    type="rect",
                    x0=x0, y0=min(y0, y1), x1=x1, y1=max(y0, y1),
                    line=dict(color=color, width=3),
                    fillcolor=color,
                    opacity=0.3,
                    name=ann['id']
                )
                
                # Agregar etiqueta
                fig.add_annotation(
                    x=x0, y=max(y0, y1),
                    text=class_name,
                    showarrow=False,
                    bgcolor=color,
                    font=dict(color="white", size=12),
                    bordercolor=color,
                    borderwidth=1
                )
            
            # Configurar layout
            fig.update_layout(
                xaxis=dict(range=[0, img_width], showgrid=False, showticklabels=False),
                yaxis=dict(range=[0, img_height], showgrid=False, showticklabels=False),
                showlegend=False,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                dragmode='drawrect'
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creando figura: {e}")
            # Crear figura vacía en caso de error
            fig = go.Figure()
            fig.update_layout(
                title="Error cargando imagen",
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False)
            )
            return fig
    
    def create_empty_metrics_chart(self):
        """Crear gráfico de métricas vacío"""
        fig = go.Figure()
        
        # Datos de ejemplo para mostrar el formato
        epochs = list(range(1, 11))
        loss_values = [0.8, 0.7, 0.65, 0.6, 0.55, 0.52, 0.5, 0.48, 0.47, 0.46]
        
        fig.add_trace(go.Scatter(
            x=epochs, y=loss_values,
            mode='lines+markers',
            name='Loss de Entrenamiento',
            line=dict(color='#00d4aa', width=3)
        ))
        
        fig.add_trace(go.Scatter(
            x=epochs, y=[0.85, 0.82, 0.85, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92, 0.93],
            mode='lines+markers',
            name='Precisión',
            line=dict(color='#ffc107', width=3)
        ))
        
        fig.update_layout(
            title="Métricas de Entrenamiento (Ejemplo)",
            xaxis_title="Época",
            yaxis_title="Valor",
            template="plotly_dark",
            legend=dict(x=0.7, y=0.95),
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return fig
    
    def create_directory_tree(self):
        """Crear árbol de directorios"""
        try:
            current_dir = os.getcwd()
            items = []
            
            # Agregar directorio actual
            items.append(
                dbc.ListGroupItem([
                    html.I(className="fas fa-folder me-2 text-warning"),
                    "📁 " + os.path.basename(current_dir) or current_dir,
                ], active=True, className="py-1")
            )
            
            # Agregar subdirectorios importantes
            important_dirs = []
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    important_dirs.append(item)
            
            # Mostrar solo los primeros 10 directorios
            for dir_name in sorted(important_dirs)[:10]:
                icon = "🎯" if "cruce" in dir_name.lower() else "📂"
                items.append(
                    dbc.ListGroupItem([
                        html.I(className="fas fa-folder me-2 text-info"),
                        f"{icon} {dir_name}",
                    ], className="py-1 ps-4", action=True, id={"type": "dir-item", "name": dir_name})
                )
            
            return dbc.ListGroup(items, flush=True)
            
        except Exception as e:
            return dbc.Alert(f"Error cargando directorios: {str(e)}", color="danger")
    
    def create_file_browser(self):
        """Crear navegador de archivos"""
        try:
            current_dir = os.getcwd()
            items = []
            
            # Obtener archivos y directorios
            entries = []
            for item in os.listdir(current_dir):
                item_path = os.path.join(current_dir, item)
                stat = os.stat(item_path)
                size = stat.st_size
                
                entries.append({
                    'name': item,
                    'is_dir': os.path.isdir(item_path),
                    'size': size,
                    'path': item_path
                })
            
            # Ordenar: directorios primero, luego archivos
            entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            # Crear elementos de la lista
            for entry in entries[:20]:  # Limitar a 20 elementos
                if entry['is_dir']:
                    icon = "📁"
                    size_text = "Directorio"
                    color = "info"
                else:
                    # Determinar icono según extensión
                    ext = os.path.splitext(entry['name'])[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                        icon = "🖼️"
                        color = "success"
                    elif ext in ['.mp4', '.avi', '.mov']:
                        icon = "🎬"
                        color = "warning"
                    elif ext in ['.txt', '.yaml', '.yml']:
                        icon = "📝"
                        color = "primary"
                    elif ext == '.py':
                        icon = "🐍"
                        color = "danger"
                    else:
                        icon = "📄"
                        color = "secondary"
                    
                    # Formatear tamaño
                    if entry['size'] < 1024:
                        size_text = f"{entry['size']} B"
                    elif entry['size'] < 1024*1024:
                        size_text = f"{entry['size']/1024:.1f} KB"
                    else:
                        size_text = f"{entry['size']/(1024*1024):.1f} MB"
                
                items.append(
                    dbc.ListGroupItem([
                        dbc.Row([
                            dbc.Col([
                                html.Span([icon, " ", entry['name']], className="fw-bold")
                            ], md=8),
                            dbc.Col([
                                dbc.Badge(size_text, color=color, className="float-end")
                            ], md=4)
                        ])
                    ], 
                    action=True, 
                    className="py-2",
                    id={"type": "file-item", "name": entry['name']}
                    )
                )
            
            if not items:
                items.append(
                    dbc.ListGroupItem("📂 Directorio vacío", className="text-muted text-center py-4")
                )
            
            return dbc.ListGroup(items, flush=True)
            
        except Exception as e:
            return dbc.Alert(f"Error cargando archivos: {str(e)}", color="danger")
    
    def get_project_statistics(self):
        """Obtener estadísticas del proyecto"""
        try:
            current_dir = os.getcwd()
            
            total_images = 0
            total_annotations = 0
            total_datasets = 0
            total_size = 0
            
            for root, dirs, files in os.walk(current_dir):
                # Contar datasets (directorios que contienen imágenes)
                image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if image_files:
                    total_datasets += 1
                    total_images += len(image_files)
                
                # Contar anotaciones
                annotation_files = [f for f in files if f.endswith('.txt')]
                total_annotations += len(annotation_files)
                
                # Calcular tamaño total
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        continue
            
            # Formatear tamaño
            if total_size < 1024*1024:
                size_str = f"{total_size/1024:.1f} KB"
            elif total_size < 1024*1024*1024:
                size_str = f"{total_size/(1024*1024):.1f} MB"
            else:
                size_str = f"{total_size/(1024*1024*1024):.1f} GB"
            
            return {
                'images': str(total_images),
                'annotations': str(total_annotations),
                'datasets': str(total_datasets),
                'size': size_str
            }
        
        except Exception as e:
            return {
                'images': "Error",
                'annotations': "Error", 
                'datasets': "Error",
                'size': "Error"
            }
        
    def create_navbar(self):
        """Crear la barra de navegación"""
        return dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("🏠 Inicio", id="nav-home", href="#", active="exact")),
                dbc.NavItem(dbc.NavLink("🏷️ Anotación", id="nav-annotation", href="#")),
                dbc.NavItem(dbc.NavLink("🤖 AutoDistill", id="nav-autodistill", href="#")),
                dbc.NavItem(dbc.NavLink("📁 Archivos", id="nav-files", href="#")),
            ],
            brand="AutoDistill Suite",
            brand_href="#",
            color="dark",
            dark=True,
            className="mb-4"
        )
    
    def create_home_page(self):
        """Crear la página de inicio"""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 AutoDistill Suite", className="text-center mb-4"),
                    html.P("Suite completa para anotación de datos y entrenamiento automático", 
                          className="text-center text-muted mb-5")
                ])
            ]),
            
            # Cards de navegación
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("🏷️ Herramienta de Anotación", className="card-title"),
                            html.P("Crea y edita bounding boxes en tus imágenes con una interfaz similar a CVAT"),
                            dbc.Button("Abrir Herramienta", id="btn-annotation", color="primary", size="lg")
                        ])
                    ], className="hover-card mb-4")
                ], md=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("🤖 AutoDistill", className="card-title"),
                            html.P("Entrena modelos automáticamente usando técnicas de destilación"),
                            dbc.Button("Configurar AutoDistill", id="btn-autodistill", color="info", size="lg")
                        ])
                    ], className="hover-card mb-4")
                ], md=6),
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("📁 Gestión de Archivos", className="card-title"),
                            html.P("Organiza tus datasets, videos y proyectos"),
                            dbc.Button("Abrir Gestor", id="btn-file-manager", color="success", size="lg")
                        ])
                    ], className="hover-card mb-4")
                ], md=6),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("📊 Estado del Sistema", className="card-title"),
                            html.P(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"),
                            dbc.Alert("Sistema funcionando correctamente ✅", color="success")
                        ])
                    ], className="hover-card mb-4")
                ], md=6),
            ]),
            
            # Información adicional
            dbc.Row([
                dbc.Col([
                    dbc.Alert([
                        html.H4("💡 Consejos de Uso", className="alert-heading"),
                        html.P("1. Comienza organizando tus archivos en el Gestor de Archivos"),
                        html.P("2. Usa la Herramienta de Anotación para etiquetar tus datos"),
                        html.P("3. Configura AutoDistill para entrenar modelos automáticamente"),
                    ], color="info", className="mb-4")
                ])
            ])
        ], fluid=True)
    
    def create_annotation_page(self):
        """Crear la página de anotación"""
        return dbc.Container([
            # Header con navegación
            dbc.Row([
                dbc.Col([
                    html.H2("🏷️ Herramienta de Anotación", className="mb-3"),
                    dbc.ButtonGroup([
                        dbc.Button("← Volver al Inicio", id="back-home", color="secondary"),
                        dbc.Button("📁 Cambiar Dataset", id="btn-change-dataset", color="info"),
                        dbc.Button("⚙️ Configurar Clases", id="btn-config-classes", color="warning")
                    ], className="mb-4")
                ])
            ]),
            
            # Selector de dataset
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📂 Configuración del Dataset"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Seleccionar Dataset:"),
                                    dcc.Dropdown(
                                        id="dataset-selector",
                                        options=[
                                            {"label": "🎯 CRUCE_COLON_1_class", "value": "CRUCE_COLON_1_class"},
                                            {"label": "🚗 dataset_cruce_3", "value": "dataset_cruce_3"},
                                        ],
                                        value="CRUCE_COLON_1_class",
                                        className="mb-3"
                                    )
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("Clases Disponibles:"),
                                    html.Div(id="classes-display", className="p-2 bg-secondary rounded")
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Herramienta principal de anotación
            dbc.Row([
                # Panel izquierdo - Controles
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🎮 Controles"),
                        dbc.CardBody([
                            # Navegación de imágenes
                            html.H6("📸 Navegación"),
                            dbc.ButtonGroup([
                                dbc.Button("⬅️", id="btn-prev-image", color="primary", size="sm"),
                                dbc.Button("➡️", id="btn-next-image", color="primary", size="sm")
                            ], className="mb-3 d-block"),
                            
                            # Info de imagen actual
                            dbc.Alert(id="current-image-info", color="info", className="mb-3"),
                            
                            # Herramientas de anotación
                            html.H6("✏️ Herramientas"),
                            dbc.ButtonGroup([
                                dbc.Button("➕ Nueva Caja", id="btn-add-box", color="success", size="sm"),
                                dbc.Button("🗑️ Eliminar", id="btn-delete-box", color="danger", size="sm")
                            ], className="mb-3 d-block"),
                            
                            # Configuración de clase
                            html.H6("🏷️ Clase Actual"),
                            dcc.Dropdown(
                                id="current-class-selector",
                                options=[{"label": "Clase 0", "value": 0}],
                                value=0,
                                className="mb-3"
                            ),
                            
                            # Acciones
                            html.H6("💾 Acciones"),
                            dbc.ButtonGroup([
                                dbc.Button("💾 Guardar", id="btn-save", color="success", size="sm"),
                                dbc.Button("↶ Deshacer", id="btn-undo", color="warning", size="sm")
                            ], className="d-block")
                        ])
                    ])
                ], md=3),
                
                # Panel central - Imagen y anotaciones
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🖼️ Editor de Imagen"),
                        dbc.CardBody([
                            # Contenedor para el gráfico
                            dcc.Graph(
                                id="annotation-graph",
                                config={
                                    'displayModeBar': True,
                                    'modeBarButtonsToAdd': ['drawrect', 'eraseshape'],
                                    'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d']
                                },
                                style={"height": "70vh"}
                            ),
                            
                            # Información de coordenadas
                            html.Div(id="coords-info", className="mt-2 text-muted")
                        ])
                    ])
                ], md=9)
            ]),
            
            # Panel inferior - Lista de anotaciones
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📋 Anotaciones Actuales"),
                        dbc.CardBody([
                            html.Div(id="annotations-list")
                        ])
                    ], className="mt-4")
                ])
            ]),
            
            # Stores para datos
            dcc.Store(id="current-annotations", data=[]),
            dcc.Store(id="current-image-data", data={}),
            dcc.Store(id="undo-stack", data=[])
            
        ], fluid=True)
    
    def create_autodistill_page(self):
        """Crear la página de AutoDistill"""
        return dbc.Container([
            # Header con navegación
            dbc.Row([
                dbc.Col([
                    html.H2("🤖 AutoDistill - Entrenamiento Automático", className="mb-3"),
                    dbc.ButtonGroup([
                        dbc.Button("← Volver al Inicio", id="back-home-autodistill", color="secondary"),
                        dbc.Button("📖 Documentación", id="btn-autodistill-docs", color="info"),
                        dbc.Button("🔄 Refrescar Estado", id="btn-refresh-status", color="warning")
                    ], className="mb-4")
                ])
            ]),
            
            # Estado del sistema
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Estado del Sistema"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Alert([
                                        html.H6("🟢 Sistema Activo", className="mb-1"),
                                        html.P("AutoDistill está listo para usar", className="mb-0")
                                    ], color="success")
                                ], md=4),
                                dbc.Col([
                                    dbc.Alert([
                                        html.H6("📈 Modelos Disponibles", className="mb-1"),
                                        html.P("5 modelos base detectados", className="mb-0")
                                    ], color="info")
                                ], md=4),
                                dbc.Col([
                                    dbc.Alert([
                                        html.H6("💾 Espacio Libre", className="mb-1"),
                                        html.P("15.2 GB disponibles", className="mb-0")
                                    ], color="warning")
                                ], md=4)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Configuración de modelo
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("⚙️ Configuración del Modelo"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("🎯 Modelo Base (Teacher):"),
                                    dcc.Dropdown(
                                        id="teacher-model-selector",
                                        options=[
                                            {"label": "🦾 CLIP (Recomendado)", "value": "clip"},
                                            {"label": "🔍 OWL-ViT", "value": "owlvit"},
                                            {"label": "📷 GroundingSAM", "value": "groundingsam"},
                                            {"label": "🎨 BLIP", "value": "blip"},
                                            {"label": "⚡ FastSAM", "value": "fastsam"}
                                        ],
                                        value="clip",
                                        className="mb-3"
                                    )
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("🎓 Modelo Estudiante (Student):"),
                                    dcc.Dropdown(
                                        id="student-model-selector",
                                        options=[
                                            {"label": "🚀 YOLOv8n (Rápido)", "value": "yolov8n"},
                                            {"label": "⚖️ YOLOv8s (Balanceado)", "value": "yolov8s"},
                                            {"label": "💪 YOLOv8m (Robusto)", "value": "yolov8m"},
                                            {"label": "🎯 YOLOv8l (Preciso)", "value": "yolov8l"}
                                        ],
                                        value="yolov8n",
                                        className="mb-3"
                                    )
                                ], md=6)
                            ]),
                            
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("📂 Dataset de Entrada:"),
                                    dcc.Dropdown(
                                        id="input-dataset-selector",
                                        options=[
                                            {"label": "🎯 CRUCE_COLON_1_class", "value": "CRUCE_COLON_1_class"},
                                            {"label": "🚗 dataset_cruce_3", "value": "dataset_cruce_3"},
                                            {"label": "📁 Seleccionar carpeta...", "value": "custom"}
                                        ],
                                        value="CRUCE_COLON_1_class",
                                        className="mb-3"
                                    )
                                ], md=6),
                                dbc.Col([
                                    dbc.Label("🏷️ Clases a Detectar:"),
                                    dbc.Textarea(
                                        id="class-prompts",
                                        placeholder="Escribe las clases separadas por comas:\nejemplo: carro, persona, bicicleta",
                                        value="carro, vehiculo",
                                        rows=3,
                                        className="mb-3"
                                    )
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ], md=8),
                
                # Panel de configuración avanzada
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🔧 Configuración Avanzada"),
                        dbc.CardBody([
                            dbc.Label("🎚️ Confianza Mínima:"),
                            dcc.Slider(
                                id="confidence-threshold",
                                min=0.1, max=0.9, step=0.1,
                                value=0.5,
                                marks={i/10: f"{i/10}" for i in range(1, 10)},
                                className="mb-3"
                            ),
                            
                            dbc.Label("📏 Tamaño de Imagen:"),
                            dcc.Dropdown(
                                id="image-size",
                                options=[
                                    {"label": "416x416 (Rápido)", "value": 416},
                                    {"label": "640x640 (Estándar)", "value": 640},
                                    {"label": "832x832 (Preciso)", "value": 832}
                                ],
                                value=640,
                                className="mb-3"
                            ),
                            
                            dbc.Checklist(
                                id="advanced-options",
                                options=[
                                    {"label": "🔄 Augmentación de datos", "value": "augment"},
                                    {"label": "📊 Validación automática", "value": "validate"},
                                    {"label": "💾 Guardar checkpoints", "value": "checkpoints"}
                                ],
                                value=["augment", "validate"],
                                className="mb-3"
                            )
                        ])
                    ])
                ], md=4)
            ]),
            
            # Panel de ejecución
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🚀 Ejecutar AutoDistill"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button("▶️ Iniciar Entrenamiento", id="btn-start-training", 
                                                 color="success", size="lg", className="me-2"),
                                        dbc.Button("⏸️ Pausar", id="btn-pause-training", 
                                                 color="warning", size="lg", disabled=True),
                                        dbc.Button("⏹️ Detener", id="btn-stop-training", 
                                                 color="danger", size="lg", disabled=True)
                                    ], className="mb-3")
                                ], md=8),
                                dbc.Col([
                                    html.H6("📈 Progreso Actual"),
                                    dbc.Progress(id="training-progress", value=0, className="mb-2"),
                                    html.Small(id="training-status", className="text-muted")
                                ], md=4)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Monitor de entrenamiento
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Monitor de Entrenamiento"),
                        dbc.CardBody([
                            dcc.Graph(
                                id="training-metrics-graph",
                                figure=self.create_empty_metrics_chart(),
                                style={"height": "400px"}
                            )
                        ])
                    ], className="mb-4")
                ], md=8),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📝 Log de Eventos"),
                        dbc.CardBody([
                            html.Div(
                                id="training-log",
                                children=[
                                    html.P("🔄 Sistema iniciado", className="mb-1 text-success"),
                                    html.P("📂 Datasets cargados", className="mb-1 text-info"),
                                    html.P("⚡ Listo para entrenar", className="mb-1 text-warning")
                                ],
                                style={"max-height": "350px", "overflow-y": "auto"}
                            )
                        ])
                    ])
                ], md=4)
            ]),
            
            # Stores para datos
            dcc.Store(id="autodistill-config", data={}),
            dcc.Store(id="training-state", data={"status": "idle", "progress": 0}),
            dcc.Interval(id="training-interval", interval=2000, n_intervals=0, disabled=True)
            
        ], fluid=True)
    
    def create_files_page(self):
        """Crear la página de gestión de archivos"""
        return dbc.Container([
            # Header con navegación
            dbc.Row([
                dbc.Col([
                    html.H2("📁 Gestión de Archivos y Proyectos", className="mb-3"),
                    dbc.ButtonGroup([
                        dbc.Button("← Volver al Inicio", id="back-home-files", color="secondary"),
                        dbc.Button("🔄 Refrescar", id="btn-refresh-files", color="info"),
                        dbc.Button("📊 Estadísticas", id="btn-show-stats", color="warning")
                    ], className="mb-4")
                ])
            ]),
            
            # Información del directorio actual
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📍 Directorio Actual"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H5(os.getcwd(), className="text-info mb-2"),
                                    dbc.Breadcrumb(
                                        items=[
                                            {"label": "🏠 Inicio", "href": "#", "active": False},
                                            {"label": "AutoDistill", "href": "#", "active": False},
                                            {"label": "Workspace", "href": "#", "active": True}
                                        ]
                                    )
                                ], md=8),
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button("📁 Nueva Carpeta", id="btn-new-folder", color="success", size="sm"),
                                        dbc.Button("📤 Subir Archivo", id="btn-upload-file", color="primary", size="sm")
                                    ])
                                ], md=4, className="text-end")
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Explorador de archivos
            dbc.Row([
                # Panel izquierdo - Árbol de directorios
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🌳 Estructura de Directorios"),
                        dbc.CardBody([
                            html.Div(id="directory-tree", children=self.create_directory_tree()),
                            html.Hr(),
                            dbc.Button("🔍 Escanear Nuevos Datasets", 
                                     id="btn-scan-datasets", color="info", size="sm", className="w-100")
                        ])
                    ])
                ], md=4),
                
                # Panel derecho - Contenido del directorio
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            dbc.Row([
                                dbc.Col([
                                    html.H6("📂 Contenido del Directorio", className="mb-0")
                                ], md=6),
                                dbc.Col([
                                    dbc.InputGroup([
                                        dbc.Input(placeholder="Buscar archivos...", id="file-search-input"),
                                        dbc.Button("🔍", id="btn-search-files", color="outline-secondary")
                                    ], size="sm")
                                ], md=6)
                            ])
                        ]),
                        dbc.CardBody([
                            html.Div(id="file-browser", children=self.create_file_browser()),
                        ], style={"max-height": "60vh", "overflow-y": "auto"})
                    ])
                ], md=8)
            ]),
            
            # Estadísticas y herramientas
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Estadísticas del Proyecto"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H4("📸", className="text-center mb-2"),
                                            html.H5(id="total-images", className="text-center text-info"),
                                            html.P("Imágenes Totales", className="text-center text-muted mb-0")
                                        ])
                                    ])
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H4("🏷️", className="text-center mb-2"),
                                            html.H5(id="total-annotations", className="text-center text-success"),
                                            html.P("Anotaciones", className="text-center text-muted mb-0")
                                        ])
                                    ])
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H4("📁", className="text-center mb-2"),
                                            html.H5(id="total-datasets", className="text-center text-warning"),
                                            html.P("Datasets", className="text-center text-muted mb-0")
                                        ])
                                    ])
                                ], md=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H4("💾", className="text-center mb-2"),
                                            html.H5(id="total-size", className="text-center text-danger"),
                                            html.P("Espacio Usado", className="text-center text-muted mb-0")
                                        ])
                                    ])
                                ], md=3)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Herramientas de archivo
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🛠️ Herramientas de Archivo"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button("🎬 Extraer Frames de Video", 
                                             id="btn-extract-frames", color="primary", size="sm", className="w-100 mb-2"),
                                    dbc.Button("📝 Convertir Formato de Etiquetas", 
                                             id="btn-convert-labels", color="info", size="sm", className="w-100 mb-2")
                                ], md=4),
                                dbc.Col([
                                    dbc.Button("🔄 Reorganizar Dataset", 
                                             id="btn-reorganize-dataset", color="warning", size="sm", className="w-100 mb-2"),
                                    dbc.Button("📊 Validar Anotaciones", 
                                             id="btn-validate-annotations", color="success", size="sm", className="w-100 mb-2")
                                ], md=4),
                                dbc.Col([
                                    dbc.Button("🗜️ Comprimir Proyecto", 
                                             id="btn-compress-project", color="secondary", size="sm", className="w-100 mb-2"),
                                    dbc.Button("📤 Exportar Dataset", 
                                             id="btn-export-dataset", color="danger", size="sm", className="w-100 mb-2")
                                ], md=4)
                            ])
                        ])
                    ])
                ])
            ]),
            
            # Modal para operaciones de archivo
            dbc.Modal([
                dbc.ModalHeader("🔧 Operación de Archivo"),
                dbc.ModalBody(id="file-operation-modal-body"),
                dbc.ModalFooter([
                    dbc.Button("Cerrar", id="btn-close-modal", color="secondary"),
                    dbc.Button("Ejecutar", id="btn-execute-operation", color="primary")
                ])
            ], id="file-operation-modal", is_open=False),
            
            # Stores para datos
            dcc.Store(id="current-directory", data=os.getcwd()),
            dcc.Store(id="selected-files", data=[]),
            dcc.Store(id="file-stats", data={})
            
        ], fluid=True)
    
    def setup_layout(self):
        """Configurar el layout principal"""
        self.app.layout = dbc.Container([
            # Store para mantener el estado de la página actual
            dcc.Store(id='current-page', data={'page': 'home'}),
            
            # Navbar
            self.create_navbar(),
            
            # Contenido principal
            html.Div(id='page-content', children=self.create_home_page())
            
        ], fluid=True, className="p-0")
    
    def setup_callbacks(self):
        """Configurar los callbacks de navegación"""
        
        @self.app.callback(
            [Output('page-content', 'children'),
             Output('current-page', 'data')],
            [Input('nav-home', 'n_clicks'),
             Input('nav-annotation', 'n_clicks'),
             Input('nav-autodistill', 'n_clicks'),
             Input('nav-files', 'n_clicks'),
             Input('btn-annotation', 'n_clicks'),
             Input('btn-autodistill', 'n_clicks'),
             Input('btn-file-manager', 'n_clicks')],
            [State('current-page', 'data')],
            prevent_initial_call=False
        )
        def navigate_pages(nav_home, nav_annotation, nav_autodistill, nav_files,
                          btn_annotation, btn_autodistill, btn_files, current_page):
            """Manejar la navegación entre páginas"""
            
            ctx = callback_context
            if not ctx.triggered:
                return self.create_home_page(), {'page': 'home'}
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Navegación por navbar
            if button_id == 'nav-home':
                return self.create_home_page(), {'page': 'home'}
            elif button_id in ['nav-annotation', 'btn-annotation']:
                return self.create_annotation_page(), {'page': 'annotation'}
            elif button_id in ['nav-autodistill', 'btn-autodistill']:
                return self.create_autodistill_page(), {'page': 'autodistill'}
            elif button_id in ['nav-files', 'btn-file-manager']:
                return self.create_files_page(), {'page': 'files'}
            
            # Por defecto, mantener la página actual
            current_page = current_page or {'page': 'home'}
            if current_page['page'] == 'home':
                return self.create_home_page(), current_page
            elif current_page['page'] == 'annotation':
                return self.create_annotation_page(), current_page
            elif current_page['page'] == 'autodistill':
                return self.create_autodistill_page(), current_page
            elif current_page['page'] == 'files':
                return self.create_files_page(), current_page
            else:
                return self.create_home_page(), {'page': 'home'}
        
        # Callbacks adicionales para botones "Volver al Inicio"
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home', 'n_clicks'),
             Input('back-home-autodistill', 'n_clicks'),
             Input('back-home-files', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home(back1, back2, back3):
            """Volver al inicio desde cualquier página"""
            ctx = callback_context
            if ctx.triggered:
                return self.create_home_page(), {'page': 'home'}
            return dash.no_update, dash.no_update
        
        # Callbacks para la herramienta de anotación
        @self.app.callback(
            [Output('classes-display', 'children'),
             Output('current-class-selector', 'options')],
            [Input('dataset-selector', 'value')]
        )
        def update_classes_display(selected_dataset):
            """Actualizar display de clases"""
            if selected_dataset:
                self.current_dataset = selected_dataset
                self.classes = self.load_classes_from_yaml()
            
            # Crear display de clases
            class_badges = []
            options = []
            
            for class_id, class_name in self.classes.items():
                color = px.colors.qualitative.Set1[class_id % len(px.colors.qualitative.Set1)]
                class_badges.append(
                    dbc.Badge(
                        f"{class_id}: {class_name}",
                        color="primary",
                        className="me-2 mb-1"
                    )
                )
                options.append({"label": f"{class_id}: {class_name}", "value": class_id})
            
            return class_badges, options
        
        @self.app.callback(
            [Output('annotation-graph', 'figure'),
             Output('current-image-info', 'children'),
             Output('current-annotations', 'data')],
            [Input('btn-prev-image', 'n_clicks'),
             Input('btn-next-image', 'n_clicks'),
             Input('dataset-selector', 'value')],
            [State('current-annotations', 'data')]
        )
        def navigate_images(prev_clicks, next_clicks, dataset, current_annotations):
            """Navegar entre imágenes"""
            ctx = callback_context
            
            # Obtener archivos de imagen del dataset actual
            image_files = self.get_image_files(self.current_dataset)
            
            if not image_files:
                empty_fig = go.Figure()
                empty_fig.update_layout(title="No hay imágenes en el dataset seleccionado")
                return empty_fig, "No hay imágenes disponibles", []
            
            # Determinar dirección de navegación
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if button_id == 'btn-prev-image' and prev_clicks:
                    self.current_image_index = (self.current_image_index - 1) % len(image_files)
                elif button_id == 'btn-next-image' and next_clicks:
                    self.current_image_index = (self.current_image_index + 1) % len(image_files)
            
            # Cargar imagen y anotaciones
            current_image = image_files[self.current_image_index]
            image_path = os.path.join(self.current_dataset, current_image)
            
            # Cargar anotaciones existentes
            annotations = self.load_yolo_annotations(current_image, self.current_dataset)
            
            # Crear figura
            if os.path.exists(image_path):
                fig = self.create_annotation_figure(image_path, annotations)
            else:
                fig = go.Figure()
                fig.update_layout(title="Error: Imagen no encontrada")
            
            # Info de imagen actual
            info_text = f"📸 {current_image} ({self.current_image_index + 1}/{len(image_files)}) | 📋 {len(annotations)} anotaciones"
            
            return fig, info_text, annotations
        
        @self.app.callback(
            Output('annotations-list', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_annotations_list(annotations):
            """Actualizar lista de anotaciones"""
            if not annotations:
                return dbc.Alert("No hay anotaciones en esta imagen", color="info")
            
            items = []
            for i, ann in enumerate(annotations):
                class_name = self.classes.get(ann['class_id'], f"Clase {ann['class_id']}")
                color = px.colors.qualitative.Set1[ann['class_id'] % len(px.colors.qualitative.Set1)]
                
                items.append(
                    dbc.ListGroupItem([
                        dbc.Row([
                            dbc.Col([
                                dbc.Badge(class_name, color="primary", className="me-2"),
                                f"ID: {ann['id']}"
                            ], md=8),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("✏️", size="sm", color="warning", id={"type": "edit-ann", "index": i}),
                                    dbc.Button("🗑️", size="sm", color="danger", id={"type": "delete-ann", "index": i})
                                ], size="sm")
                            ], md=4, className="text-end")
                        ])
                    ])
                )
            
            return dbc.ListGroup(items)
        
        # Callback para actualizar estadísticas del proyecto
        @self.app.callback(
            [Output('total-images', 'children'),
             Output('total-annotations', 'children'),
             Output('total-datasets', 'children'),
             Output('total-size', 'children')],
            [Input('btn-refresh-files', 'n_clicks'),
             Input('page-content', 'children')],
            prevent_initial_call=True
        )
        def update_project_statistics(refresh_clicks, page_content):
            """Actualizar estadísticas del proyecto"""
            stats = self.get_project_statistics()
            return stats['images'], stats['annotations'], stats['datasets'], stats['size']
        
        # Callback para manejar clics en archivos y directorios  
        @self.app.callback(
            Output('file-browser', 'children'),
            [Input({'type': 'dir-item', 'name': ALL}, 'n_clicks'),
             Input({'type': 'file-item', 'name': ALL}, 'n_clicks')],
            prevent_initial_call=True
        )
        def handle_file_clicks(dir_clicks, file_clicks):
            """Manejar clics en archivos y directorios"""
            ctx = callback_context
            if ctx.triggered:
                # Por ahora, solo refrescar el navegador
                return self.create_file_browser()
            return dash.no_update

def main():
    """Función principal"""
    try:
        # Crear la aplicación
        suite = AutoDistillSuite(app)
        suite.setup_layout()
        suite.setup_callbacks()
        
        print("🚀 Iniciando AutoDistill Suite...")
        print(f"📁 Directorio de trabajo: {os.getcwd()}")
        print("🌐 Abriendo en: http://localhost:8050")
        print("✅ Aplicación lista!")
        
        # Ejecutar la aplicación
        app.run_server(
            debug=True,
            host='localhost',
            port=8050,
            dev_tools_hot_reload=True
        )
        
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()