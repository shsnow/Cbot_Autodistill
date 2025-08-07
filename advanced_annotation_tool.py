"""
Herramienta Avanzada de Corrección de Etiquetado - Similar a CVAT
Permite editar anotaciones YOLO de manera interactiva con manipulación de bounding boxes
"""

import dash
from dash import dcc, html, callback, Input, Output, State, ctx, ALL, MATCH, clientside_callback, ClientsideFunction, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import base64
from PIL import Image
import io
import cv2
import numpy as np

class AdvancedAnnotationTool:
    def __init__(self, dataset_path="dataset_cruce_3"):
        self.dataset_path = dataset_path
        self.images_path = os.path.join(dataset_path, "train", "images")
        self.labels_path = os.path.join(dataset_path, "train", "labels")
        self.classes = ["vehículo"]  # Basado en tu ontología
        self.current_image_index = 0
        
        # Verificar que los directorios existen
        if not os.path.exists(self.images_path):
            raise FileNotFoundError(f"Directorio de imágenes no encontrado: {self.images_path}")
        
        self.image_files = sorted([f for f in os.listdir(self.images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        if not self.image_files:
            raise FileNotFoundError(f"No se encontraron imágenes en: {self.images_path}")
        
        # Configurar la app Dash
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])  # Tema oscuro
        self.setup_layout()
        self.setup_callbacks()
    
    def load_image_annotations(self, image_filename):
        """Cargar anotaciones para una imagen específica"""
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        annotations = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line_idx, line in enumerate(f.readlines()):
                    line = line.strip()
                    if line:
                        try:
                            parts = line.split()
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            # Validar que los valores estén en rango válido
                            if (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                0 <= width <= 1 and 0 <= height <= 1 and
                                class_id < len(self.classes)):
                                
                                annotations.append({
                                    'id': line_idx,
                                    'class_id': class_id,
                                    'class_name': self.classes[class_id],
                                    'x_center': x_center,
                                    'y_center': y_center,
                                    'width': width,
                                    'height': height
                                })
                        except (ValueError, IndexError) as e:
                            print(f"Error leyendo línea {line_idx + 1} en {label_filename}: {e}")
                            continue
        
        return annotations
    
    def save_annotations(self, image_filename, annotations):
        """Guardar anotaciones en formato YOLO"""
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        if not annotations:
            # Si no hay anotaciones, crear archivo vacío o eliminarlo
            if os.path.exists(label_path):
                os.remove(label_path)
            return
        
        with open(label_path, 'w') as f:
            for ann in annotations:
                line = f"{ann['class_id']} {ann['x_center']:.6f} {ann['y_center']:.6f} {ann['width']:.6f} {ann['height']:.6f}\n"
                f.write(line)
    
    def yolo_to_pixel_coords(self, annotation, img_width, img_height):
        """Convertir coordenadas YOLO normalizadas a píxeles"""
        x_center = annotation['x_center'] * img_width
        y_center = annotation['y_center'] * img_height
        width = annotation['width'] * img_width
        height = annotation['height'] * img_height
        
        x_min = max(0, x_center - width / 2)
        y_min = max(0, y_center - height / 2)
        x_max = min(img_width, x_center + width / 2)
        y_max = min(img_height, y_center + height / 2)
        
        return x_min, y_min, x_max, y_max
    
    def pixel_to_yolo_coords(self, x_min, y_min, x_max, y_max, img_width, img_height):
        """Convertir coordenadas de píxeles a formato YOLO normalizado"""
        # Asegurar que las coordenadas están dentro de los límites
        x_min = max(0, min(x_min, img_width))
        y_min = max(0, min(y_min, img_height))
        x_max = max(0, min(x_max, img_width))
        y_max = max(0, min(y_max, img_height))
        
        # Asegurar que x_max > x_min y y_max > y_min
        if x_max <= x_min:
            x_max = x_min + 1
        if y_max <= y_min:
            y_max = y_min + 1
        
        x_center = ((x_min + x_max) / 2) / img_width
        y_center = ((y_min + y_max) / 2) / img_height
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height
        
        # Asegurar que los valores están normalizados
        x_center = max(0, min(1, x_center))
        y_center = max(0, min(1, y_center))
        width = max(0, min(1, width))
        height = max(0, min(1, height))
        
        return x_center, y_center, width, height
    
    def get_image_as_base64(self, image_path):
        """Convertir imagen a base64 para mostrar en Dash"""
        with open(image_path, "rb") as img_file:
            img_str = base64.b64encode(img_file.read()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    
    def setup_layout(self):
        """Configurar el layout de la aplicación"""
        self.app.layout = dbc.Container([
            # Stores para mantener el estado
            dcc.Store(id='current-annotations', data=[]),
            dcc.Store(id='current-image-data', data={}),
            dcc.Store(id='image-dimensions', data={}),
            dcc.Store(id='selected-annotation', data=None),
            dcc.Store(id='keyboard-trigger', data=0),  # Para atajos de teclado
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🔧 Herramienta Avanzada de Corrección de Etiquetado", 
                           className="text-center mb-3", 
                           style={"color": "#00d4aa", "font-weight": "bold", "font-family": "Arial Black", 
                                  "text-shadow": "0 0 10px rgba(0,212,170,0.5)"}),
                    html.P("Edita anotaciones YOLO de manera interactiva - Similar a CVAT",
                           className="text-center", 
                           style={"color": "#adb5bd", "font-size": "1.1rem", "margin-bottom": "2rem"}),
                    html.Hr(style={"border-color": "#495057", "border-width": "2px"})
                ])
            ]),
            
            # Control Panel
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("📂 Navegación:", className="fw-bold mb-2", 
                                     style={"color": "#00d4aa", "font-family": "Arial Black"}),
                            dbc.ButtonGroup([
                                dbc.Button("◀◀ Primero", id="first-button", color="outline-info", size="sm", className="shadow-sm"),
                                dbc.Button("◀ Anterior", id="prev-button", color="info", size="sm", className="shadow-sm"),
                                dbc.Button("Siguiente ▶", id="next-button", color="info", size="sm", className="shadow-sm"),
                                dbc.Button("Último ▶▶", id="last-button", color="outline-info", size="sm", className="shadow-sm"),
                            ], className="w-100"),
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("📊 Estado:", className="fw-bold mb-2", 
                                     style={"color": "#00d4aa", "font-family": "Arial Black"}),
                            html.P(id="image-counter", className="text-center mb-0 fs-6 fw-bold",
                                  style={"color": "#adb5bd", "background": "rgba(0,212,170,0.1)", 
                                         "padding": "0.5rem", "border-radius": "0.5rem"})
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("🛠️ Herramientas:", className="fw-bold mb-2", 
                                     style={"color": "#00d4aa", "font-family": "Arial Black"}),
                            dbc.ButtonGroup([
                                dbc.Button("🗑️ Eliminar Frame", id="delete-frame-button", color="danger", size="sm", className="shadow-sm"),
                            ], className="w-100"),
                            html.Small("� Dibuja para crear • Clic para editar", className="text-muted mt-1")
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("💾 Acciones:", className="fw-bold mb-2", 
                                     style={"color": "#00d4aa", "font-family": "Arial Black"}),
                            dbc.ButtonGroup([
                                dbc.Button(" Recargar", id="reload-button", color="info", size="sm", className="shadow-sm"),
                            ]),
                            html.Small("⌨️ F=Siguiente • D=Anterior", className="text-muted mt-1")
                        ], width=3)
                    ])
                ])
            ], className="mb-3", style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                       "border": "1px solid #495057", "border-radius": "1rem"}),
            
            # Main content area
            dbc.Row([
                # Image viewer
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📸 Visor de Imágenes", className="mb-0", 
                                   style={"color": "#00d4aa", "font-family": "Arial Black"}),
                            dbc.Badge(id="annotation-count-badge", color="info", className="ms-2")
                        ], style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                 "border-bottom": "1px solid #495057"}),
                        dbc.CardBody([
                            dcc.Graph(
                                id="image-graph",
                                config={
                                    'displayModeBar': True,
                                    'modeBarButtonsToRemove': [
                                        'pan2d', 'select2d', 'lasso2d', 'resetScale2d',
                                        'zoomIn2d', 'zoomOut2d', 'autoScale2d'
                                    ],
                                    'displaylogo': False,
                                    'toImageButtonOptions': {
                                        'format': 'png',
                                        'filename': 'anotacion',
                                        'height': 500,
                                        'width': 700,
                                        'scale': 1
                                    }
                                },
                                style={'height': '65vh', 'width': '100%'}
                            ),
                            # Información de coordenadas del mouse
                            html.Div(id="mouse-coords", className="text-muted small mt-2")
                        ], style={'padding': '0.5rem', 'background': '#1a1a1a', 'border-radius': '0 0 1rem 1rem'})
                    ], style={"background": "#1a1a1a", "border": "1px solid #495057", "border-radius": "1rem"})
                ], width=8),
                
                # Sidebar with controls
                dbc.Col([
                    # Annotation list
                    dbc.Card([
                        dbc.CardHeader("🏷️ Lista de Anotaciones", 
                                     style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                           "color": "#00d4aa", "font-weight": "bold", "border-bottom": "1px solid #495057"}),
                        dbc.CardBody([
                            html.Div(id="annotations-list", style={'max-height': '300px', 'overflow-y': 'auto'})
                        ], style={"background": "#1a1a1a"})
                    ], className="mb-3", style={"background": "#1a1a1a", "border": "1px solid #495057", "border-radius": "1rem"}),
                    
                    # Class selector
                    dbc.Card([
                        dbc.CardHeader("🎨 Configuración", 
                                     style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                           "color": "#00d4aa", "font-weight": "bold", "border-bottom": "1px solid #495057"}),
                        dbc.CardBody([
                            html.Label("Clase para nuevas anotaciones:", className="mb-2", 
                                     style={"color": "#00d4aa", "font-weight": "bold"}),
                            dbc.Select(
                                id="class-selector",
                                options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                                value=0,
                                size="sm",
                                className="mb-3"
                            ),
                            html.Label("Opacidad de las cajas:", className="mb-2", 
                                     style={"color": "#00d4aa", "font-weight": "bold"}),
                            dcc.Slider(
                                id="opacity-slider",
                                min=0.1,
                                max=1.0,
                                value=0.3,
                                step=0.1,
                                marks={i/10: str(i/10) for i in range(1, 11)},
                                className="mb-3"
                            ),
                            dbc.Checklist(
                                options=[
                                    {"label": " Mostrar IDs", "value": "show_ids"},
                                    {"label": " Mostrar coordenadas", "value": "show_coords"},
                                ],
                                value=["show_ids"],
                                id="display-options",
                                inline=True
                            ),
                            html.Hr(className="my-2"),
                            html.Label("💡 Instrucciones:", className="mb-2", 
                                     style={"color": "#00d4aa", "font-weight": "bold"}),
                            dbc.Alert([
                                html.Strong("✏️ CREAR: ", style={"color": "#00d4aa"}), "Arrastra el mouse para dibujar",
                                html.Br(),
                                html.Strong("🎯 EDITAR: ", style={"color": "#00d4aa"}), "Clic directo en la caja",
                                html.Br(), 
                                html.Strong("🗑️ ELIMINAR: ", style={"color": "#00d4aa"}), "Usar botón rojo de la lista",
                                html.Br(),
                                html.Strong("⌨️ NAVEGAR: ", style={"color": "#00d4aa"}), "F=Siguiente • D=Anterior",
                                html.Br(),
                                html.Strong("💾 GUARDADO: ", style={"color": "#00d4aa"}), "Automático al editar"
                            ], color="dark", className="small", style={"background": "rgba(0,212,170,0.1)", "border": "1px solid #00d4aa"})
                        ], style={"background": "#1a1a1a"})
                    ], className="mb-3", style={"background": "#1a1a1a", "border": "1px solid #495057", "border-radius": "1rem"}),
                    
                    # Statistics
                    dbc.Card([
                        dbc.CardHeader("📈 Estadísticas", 
                                     style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                           "color": "#00d4aa", "font-weight": "bold", "border-bottom": "1px solid #495057"}),
                        dbc.CardBody([
                            html.Div(id="stats-content")
                        ], style={"background": "#1a1a1a"})
                    ], style={"background": "#1a1a1a", "border": "1px solid #495057", "border-radius": "1rem"})
                ], width=4)
            ]),
            
            # Modals
            dbc.Modal([
                dbc.ModalHeader("⚠️ Confirmar Eliminación"),
                dbc.ModalBody("¿Estás seguro de que quieres eliminar este frame? Esta acción no se puede deshacer."),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-delete", color="secondary"),
                    dbc.Button("Eliminar", id="confirm-delete", color="danger")
                ])
            ], id="delete-modal", is_open=False),
            
            # Toast para notificaciones
            dbc.Toast(
                id="notification-toast",
                header="Notificación",
                is_open=False,
                dismissable=True,
                duration=3000,
                style={"position": "fixed", "top": 66, "right": 10, "width": 350}
            ),
            
            # Div invisible para capturar eventos de teclado (sin interferir con mouse)
            html.Div(id="keyboard-listener", tabIndex=0, style={
                "position": "absolute", "top": 0, "left": 0, "width": "1px", "height": "1px",
                "opacity": 0, "pointer-events": "none", "outline": "none"
            }),
            
        ], fluid=True, style={'padding': '1rem', 'background': 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)', 'min-height': '100vh'})
    
    def create_figure_with_annotations(self, image_filename, annotations, opacity=0.3, show_ids=True, show_coords=False):
        """Crear figura de Plotly con imagen y anotaciones"""
        image_path = os.path.join(self.images_path, image_filename)
        
        if not os.path.exists(image_path):
            # Crear figura vacía si la imagen no existe
            fig = go.Figure()
            fig.update_layout(title="❌ Imagen no encontrada")
            return fig, {'width': 800, 'height': 600}
        
        # Cargar imagen
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
        except Exception as e:
            fig = go.Figure()
            fig.update_layout(title=f"❌ Error cargando imagen: {str(e)}")
            return fig, {'width': 800, 'height': 600}
        
        # Crear figura
        fig = go.Figure()
        
        # Convertir imagen a base64 y agregar como fondo
        img_base64 = self.get_image_as_base64(image_path)
        
        fig.add_layout_image(
            dict(
                source=img_base64,
                xref="x",
                yref="y",
                x=0,
                y=img_height,
                sizex=img_width,
                sizey=img_height,
                sizing="stretch",
                opacity=1,
                layer="below"
            )
        )
        
        # Agregar bounding boxes SOLO como shapes (no como trazas)
        colors = ['#00d4aa', '#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3', '#54a0ff']
        shapes = []
        
        for i, ann in enumerate(annotations):
            x_min, y_min, x_max, y_max = self.yolo_to_pixel_coords(ann, img_width, img_height)
            color = colors[ann['class_id'] % len(colors)]
            
            # Convertir coordenadas Y (Plotly usa coordenadas invertidas)
            y_min_plot = img_height - y_max
            y_max_plot = img_height - y_min
            
            # Crear shape con transparencia mejorada
            # Convertir color hex a RGB para el fillcolor con transparencia
            color_rgb = [int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
            fill_color = f"rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]},{opacity})"
            
            shape = dict(
                type="rect",
                x0=x_min, y0=y_min_plot,
                x1=x_max, y1=y_max_plot,
                line=dict(color=color, width=3),  # Línea más gruesa
                fillcolor=fill_color,  # Color con transparencia
                editable=True,
                name=f"bbox_{ann['id']}",
                xref="x",
                yref="y",
                layer="above"
            )
            shapes.append(shape)
            
            # Agregar etiqueta de texto como anotación
            if show_ids or show_coords:
                label_parts = []
                if show_ids:
                    label_parts.append(f"ID:{ann['id']}")
                label_parts.append(ann['class_name'])
                if show_coords:
                    label_parts.append(f"({ann['x_center']:.3f},{ann['y_center']:.3f})")
                
                label_text = " | ".join(label_parts)
                
                fig.add_annotation(
                    x=x_min,
                    y=y_max_plot,
                    text=label_text,
                    showarrow=False,
                    bgcolor=color,
                    bordercolor=color,
                    borderwidth=2,
                    font=dict(color="white", size=11, family="Arial Black"),
                    xanchor="left",
                    yanchor="bottom",
                    opacity=0.9
                )
        
        # Configurar ejes
        fig.update_xaxes(
            range=[0, img_width],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            fixedrange=True
        )
        
        fig.update_yaxes(
            range=[0, img_height],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True
        )
        
        fig.update_layout(
            title=dict(
                text=f"📸 {image_filename} ({img_width}×{img_height}) - ✏️ Dibuja para crear • Doble clic en caja para editar",
                font=dict(size=16, color="#00d4aa", family="Arial Black")
            ),
            showlegend=False,
            margin=dict(l=0, r=0, t=60, b=0),
            dragmode="drawrect",
            selectdirection="d",
            newshape=dict(
                line=dict(color="#00d4aa", width=3),
                fillcolor="rgba(0,212,170,0.2)"
            ),
            plot_bgcolor='#1a1a1a',
            paper_bgcolor='#1a1a1a',
            shapes=shapes,
            font=dict(color="#adb5bd")
        )
        
        return fig, {'width': img_width, 'height': img_height}
    
    def setup_callbacks(self):
        """Configurar callbacks de Dash"""
        
        # JavaScript para capturar eventos de teclado globalmente
        clientside_callback(
            """
            function(n) {
                // Remover listeners previos si existen
                if (window.keydownListener) {
                    document.removeEventListener('keydown', window.keydownListener);
                }
                
                // Crear nuevo listener
                window.keydownListener = function(event) {
                    // Solo procesar si no estamos en un input o textarea
                    if (event.target.tagName !== 'INPUT' && event.target.tagName !== 'TEXTAREA') {
                        if (event.key === 'f' || event.key === 'F') {
                            const nextBtn = document.getElementById('next-button');
                            if (nextBtn) {
                                nextBtn.click();
                                event.preventDefault();
                            }
                        } else if (event.key === 'd' || event.key === 'D') {
                            const prevBtn = document.getElementById('prev-button');
                            if (prevBtn) {
                                prevBtn.click();
                                event.preventDefault();
                            }
                        }
                    }
                };
                
                // Agregar el listener al document
                document.addEventListener('keydown', window.keydownListener);
                
                return n + 1;
            }
            """,
            Output('keyboard-trigger', 'data'),
            [Input('keyboard-listener', 'id')]
        )
        
        @self.app.callback(
            [Output('image-graph', 'figure'),
             Output('current-annotations', 'data'),
             Output('image-counter', 'children'),
             Output('image-dimensions', 'data'),
             Output('current-image-data', 'data'),
             Output('annotation-count-badge', 'children')],
            [Input('next-button', 'n_clicks'),
             Input('prev-button', 'n_clicks'),
             Input('first-button', 'n_clicks'),
             Input('last-button', 'n_clicks'),
             Input('reload-button', 'n_clicks'),
             Input('opacity-slider', 'value'),
             Input('display-options', 'value')],
            [State('current-annotations', 'data')]
        )
        def navigate_and_update_display(next_clicks, prev_clicks, first_clicks, last_clicks, 
                                      reload_clicks, opacity, display_options, current_annotations):
            """Navegar entre imágenes y actualizar display"""
            # Determinar navegación
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if button_id == 'next-button' and next_clicks:
                    self.current_image_index = min(self.current_image_index + 1, len(self.image_files) - 1)
                elif button_id == 'prev-button' and prev_clicks:
                    self.current_image_index = max(self.current_image_index - 1, 0)
                elif button_id == 'first-button' and first_clicks:
                    self.current_image_index = 0
                elif button_id == 'last-button' and last_clicks:
                    self.current_image_index = len(self.image_files) - 1
                elif button_id == 'reload-button':
                    pass  # Solo recargar sin cambiar índice
                elif button_id in ['opacity-slider', 'display-options']:
                    # Solo actualizar display, mantener anotaciones actuales
                    current_image = self.image_files[self.current_image_index]
                    show_ids = 'show_ids' in (display_options or [])
                    show_coords = 'show_coords' in (display_options or [])
                    
                    fig, img_dims = self.create_figure_with_annotations(
                        current_image, current_annotations or [], opacity, show_ids, show_coords
                    )
                    
                    counter_text = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
                    badge_text = f"{len(current_annotations or [])} anotaciones"
                    
                    return fig, current_annotations, counter_text, img_dims, {'filename': current_image}, badge_text
            
            # Cargar nueva imagen
            current_image = self.image_files[self.current_image_index]
            annotations = self.load_image_annotations(current_image)
            
            show_ids = 'show_ids' in (display_options or ['show_ids'])
            show_coords = 'show_coords' in (display_options or [])
            
            fig, img_dims = self.create_figure_with_annotations(
                current_image, annotations, opacity, show_ids, show_coords
            )
            
            counter_text = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
            badge_text = f"{len(annotations)} anotaciones"
            
            return fig, annotations, counter_text, img_dims, {'filename': current_image}, badge_text
        
        @self.app.callback(
            Output('annotations-list', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_annotations_list(annotations):
            """Actualizar lista de anotaciones en el sidebar"""
            colors = ['#00d4aa', '#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3', '#54a0ff']
            
            if not annotations:
                return [
                    dbc.Alert([
                        "📭 No hay anotaciones en esta imagen",
                        html.Br(),
                        html.Small("💡 Dibuja un rectángulo para crear una nueva", className="text-muted")
                    ], color="info", className="text-center")
                ]
            
            items = []
            for i, ann in enumerate(annotations):
                items.append(
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.H6(f"🏷️ {ann['class_name']}", className="card-title mb-1", 
                                           style={"color": "#00d4aa", "font-weight": "bold"}),
                                    html.Small(f"ID: {ann['id']}", className="text-muted"),
                                ], width=8),
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button("🗑️", id={"type": "delete-btn", "index": ann['id']}, 
                                                 size="sm", color="danger", title="Eliminar", className="shadow-sm")
                                    ], size="sm")
                                ], width=4, className="text-end")
                            ]),
                            html.Hr(className="my-2", style={"border-color": "#495057"}),
                            html.Small([
                                f"Centro: ({ann['x_center']:.3f}, {ann['y_center']:.3f})",
                                html.Br(),
                                f"Tamaño: {ann['width']:.3f} × {ann['height']:.3f}",
                                html.Br(),
                                html.Strong("💡 Doble clic para cambiar a modo edición", 
                                          className="text-info", style={"color": "#00d4aa !important"})
                            ], className="text-muted")
                        ], className="py-2", style={"background": "#2d3748"})
                    ], className="mb-2", 
                       style={"border-left": f"4px solid {colors[ann['class_id'] % len(colors)]}", 
                              "box-shadow": "0 4px 8px rgba(0,212,170,0.1)", "background": "#2d3748", 
                              "border": "1px solid #495057", "border-radius": "0.5rem"})
                )
            
            return items
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open'),
             Output('notification-toast', 'children')],
            [Input('image-graph', 'relayoutData')],
            [State('current-annotations', 'data'),
             State('image-dimensions', 'data'),
             State('current-image-data', 'data'),
             State('class-selector', 'value'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def handle_shape_interaction(relayout_data, annotations, img_dims, image_data, selected_class, opacity, display_options):
            """Manejar interacción con formas - creación y edición"""
            if not relayout_data or not img_dims or not image_data:
                return annotations or [], no_update, False, ""

            annotations = annotations or []
            
            # Detectar nueva forma dibujada
            if 'shapes' in relayout_data and relayout_data['shapes']:
                shapes = relayout_data['shapes']
                
                # Si hay más shapes que anotaciones actuales, es una nueva forma
                if len(shapes) > len(annotations):
                    new_shape = shapes[-1]  # La última forma es la nueva
                    
                    try:
                        # Obtener coordenadas
                        x0 = min(new_shape['x0'], new_shape['x1'])
                        x1 = max(new_shape['x0'], new_shape['x1'])
                        y0 = min(new_shape['y0'], new_shape['y1'])
                        y1 = max(new_shape['y0'], new_shape['y1'])
                        
                        # Convertir coordenadas Y (Plotly usa coordenadas invertidas)
                        y0_img = img_dims['height'] - y1
                        y1_img = img_dims['height'] - y0
                        
                        # Validar tamaño mínimo
                        if (x1 - x0) < 10 or (y1_img - y0_img) < 10:
                            return annotations, no_update, True, "⚠️ La caja es muy pequeña (mínimo 10x10 píxeles)"
                        
                        # Convertir a coordenadas YOLO
                        x_center, y_center, width, height = self.pixel_to_yolo_coords(
                            x0, y0_img, x1, y1_img, img_dims['width'], img_dims['height']
                        )
                        
                        # Crear nueva anotación
                        new_annotation = {
                            'id': len(annotations),
                            'class_id': selected_class,
                            'class_name': self.classes[selected_class],
                            'x_center': x_center,
                            'y_center': y_center,
                            'width': width,
                            'height': height
                        }
                        
                        new_annotations = annotations + [new_annotation]
                        
                        # Guardar automáticamente
                        try:
                            self.save_annotations(image_data['filename'], new_annotations)
                        except Exception as save_error:
                            print(f"Error guardando automáticamente: {save_error}")
                        
                        # Regenerar figura
                        show_ids = 'show_ids' in (display_options or ['show_ids'])
                        show_coords = 'show_coords' in (display_options or [])
                        fig, _ = self.create_figure_with_annotations(
                            image_data['filename'], new_annotations, opacity, show_ids, show_coords
                        )
                        
                        return new_annotations, fig, True, f"✅ Nueva caja: {self.classes[selected_class]} - Guardado automático"
                        
                    except Exception as e:
                        print(f"Error creando nueva anotación: {str(e)}")
                        return annotations, no_update, True, f"❌ Error creando caja: {str(e)}"
                
                # Si hay igual número de shapes, podría ser edición
                elif len(shapes) == len(annotations) and shapes:
                    try:
                        updated_annotations = []
                        for i, (shape, ann) in enumerate(zip(shapes, annotations)):
                            # Obtener coordenadas de la shape editada
                            x0 = min(shape['x0'], shape['x1'])
                            x1 = max(shape['x0'], shape['x1'])
                            y0 = min(shape['y0'], shape['y1'])
                            y1 = max(shape['y0'], shape['y1'])
                            
                            # Convertir coordenadas Y
                            y0_img = img_dims['height'] - y1
                            y1_img = img_dims['height'] - y0
                            
                            # Validar tamaño mínimo
                            if (x1 - x0) >= 5 and (y1_img - y0_img) >= 5:
                                # Convertir a YOLO
                                x_center, y_center, width, height = self.pixel_to_yolo_coords(
                                    x0, y0_img, x1, y1_img, img_dims['width'], img_dims['height']
                                )
                                
                                # Actualizar anotación
                                updated_ann = ann.copy()
                                updated_ann['x_center'] = x_center
                                updated_ann['y_center'] = y_center
                                updated_ann['width'] = width
                                updated_ann['height'] = height
                                updated_annotations.append(updated_ann)
                            else:
                                # Mantener anotación original si es muy pequeña
                                updated_annotations.append(ann)
                        
                        # Solo guardar si algo cambió
                        if updated_annotations != annotations:
                            # Guardar automáticamente
                            try:
                                self.save_annotations(image_data['filename'], updated_annotations)
                            except Exception as save_error:
                                print(f"Error guardando automáticamente: {save_error}")
                            
                            # Regenerar figura
                            show_ids = 'show_ids' in (display_options or ['show_ids'])
                            show_coords = 'show_coords' in (display_options or [])
                            fig, _ = self.create_figure_with_annotations(
                                image_data['filename'], updated_annotations, opacity, show_ids, show_coords
                            )
                            
                            return updated_annotations, fig, True, "✏️ Caja editada - Guardado automático"
                        
                    except Exception as e:
                        print(f"Error editando anotación: {str(e)}")
                        return annotations, no_update, True, f"❌ Error editando: {str(e)}"
            
            # No hacer nada si no hay cambios relevantes
            return annotations, no_update, False, ""
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input({"type": "delete-btn", "index": ALL}, "n_clicks")],
            [State('current-annotations', 'data'),
             State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def delete_annotation(delete_clicks, annotations, image_data, opacity, display_options):
            """Eliminar anotación específica"""
            if not any(delete_clicks or []) or not ctx.triggered:
                return annotations, no_update, False, ""
            
            try:
                # Obtener el ID de la anotación a eliminar
                triggered_prop_id = ctx.triggered[0]['prop_id']
                
                # Extraer el índice del botón clickeado
                import json
                prop_id_dict = json.loads(triggered_prop_id.split('.')[0])
                delete_id = prop_id_dict['index']
                
                # Filtrar anotaciones
                original_count = len(annotations)
                annotations = [ann for ann in annotations if ann['id'] != delete_id]
                
                # Reindexar IDs
                for i, ann in enumerate(annotations):
                    ann['id'] = i
                
                if len(annotations) < original_count:
                    # Regenerar figura
                    show_ids = 'show_ids' in (display_options or ['show_ids'])
                    show_coords = 'show_coords' in (display_options or [])
                    fig, _ = self.create_figure_with_annotations(
                        image_data['filename'], annotations, opacity, show_ids, show_coords
                    )
                    
                    # Guardar automáticamente
                    try:
                        self.save_annotations(image_data['filename'], annotations)
                    except Exception as save_error:
                        print(f"Error guardando automáticamente: {save_error}")
                    
                    return annotations, fig, True, f"🗑️ Anotación eliminada - Guardado automático"
                
            except Exception as e:
                return annotations, no_update, True, f"❌ Error eliminando anotación: {str(e)}"
            
            return annotations, no_update, False, ""
        
        @self.app.callback(
            Output('stats-content', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_statistics(annotations):
            """Actualizar estadísticas"""
            if not annotations:
                return html.P("No hay datos para mostrar", className="text-muted")
            
            # Contar por clase
            class_counts = {}
            total_area = 0
            
            for ann in annotations:
                class_name = ann['class_name']
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
                total_area += ann['width'] * ann['height']
            
            avg_area = total_area / len(annotations) if annotations else 0
            
            stats = [
                html.P([html.Strong("📊 Total: ", style={"color": "#00d4aa"}), f"{len(annotations)} anotaciones"], style={"color": "#adb5bd"}),
                html.P([html.Strong("📏 Área promedio: ", style={"color": "#00d4aa"}), f"{avg_area:.4f}"], style={"color": "#adb5bd"}),
                html.Hr(style={"border-color": "#495057"}),
                html.Strong("Por clase:", style={"color": "#00d4aa"})
            ]
            
            for class_name, count in class_counts.items():
                percentage = (count / len(annotations)) * 100
                stats.append(
                    html.P([
                        html.Span(f"• {class_name}: ", style={"color": "#2c3e50", "font-weight": "bold"}),
                        dbc.Badge(f"{count} ({percentage:.1f}%)", color="dark", className="ms-1")
                    ])
                )
            
            return stats
        
        @self.app.callback(
            [Output('delete-modal', 'is_open'),
             Output('current-image-data', 'data', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input('delete-frame-button', 'n_clicks'),
             Input('confirm-delete', 'n_clicks'),
             Input('cancel-delete', 'n_clicks')],
            [State('delete-modal', 'is_open'),
             State('current-image-data', 'data')],
            prevent_initial_call=True
        )
        def handle_frame_deletion(delete_clicks, confirm_clicks, cancel_clicks, is_open, image_data):
            """Manejar eliminación de frames"""
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                
                if button_id == 'delete-frame-button' and delete_clicks:
                    return True, image_data, False, ""
                
                elif button_id == 'confirm-delete' and confirm_clicks:
                    if image_data and 'filename' in image_data:
                        try:
                            # Eliminar archivos de imagen y etiqueta
                            img_path = os.path.join(self.images_path, image_data['filename'])
                            label_path = os.path.join(self.labels_path, 
                                                    os.path.splitext(image_data['filename'])[0] + '.txt')
                            
                            files_deleted = []
                            if os.path.exists(img_path):
                                os.remove(img_path)
                                files_deleted.append("imagen")
                            if os.path.exists(label_path):
                                os.remove(label_path)
                                files_deleted.append("etiquetas")
                            
                            # Actualizar lista de archivos
                            self.image_files = sorted([f for f in os.listdir(self.images_path) 
                                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
                            
                            # Ajustar índice actual
                            if self.current_image_index >= len(self.image_files):
                                self.current_image_index = max(0, len(self.image_files) - 1)
                            
                            message = f"🗑️ Frame eliminado ({', '.join(files_deleted)})"
                            return False, image_data, True, message
                            
                        except Exception as e:
                            return False, image_data, True, f"❌ Error eliminando frame: {str(e)}"
                
                elif button_id == 'cancel-delete':
                    return False, image_data, False, ""
            
            return is_open, image_data, False, ""
    
    def run(self, debug=True, port=8050, host='127.0.0.1'):
        """Ejecutar la aplicación"""
        print("🚀 Iniciando Herramienta Avanzada de Corrección de Etiquetado...")
        print(f"📁 Dataset: {self.dataset_path}")
        print(f"🖼️ Imágenes encontradas: {len(self.image_files)}")
        print(f"🏷️ Clases disponibles: {', '.join(self.classes)}")
        print(f"🌐 Servidor iniciando en: http://{host}:{port}")
        print("\n" + "="*60)
        print("💡 INSTRUCCIONES DE USO MEJORADAS:")
        print("• ⌨️ NAVEGACIÓN RÁPIDA: Presiona 'F' para siguiente imagen, 'D' para anterior")
        print("• ✏️ CREAR NUEVAS CAJAS: Dibujar rectángulos arrastrando el mouse")
        print("• 🎯 EDITAR CAJAS EXISTENTES: Hacer clic en una caja y arrastrar esquinas/bordes")
        print("• 🗑️ ELIMINAR: Usar botones en la lista lateral o botón 'Eliminar Frame'")
        print("• 💾 GUARDADO: Automático al crear, editar o eliminar anotaciones")
        print("• 🎨 AJUSTAR: Opacidad y opciones de visualización en barra lateral")
        print("=" * 60)
        print("⌨️ ATAJOS DE TECLADO:")
        print("  • Presiona 'F' para ir a la siguiente imagen")
        print("  • Presiona 'D' para ir a la imagen anterior")
        print("  • Los cambios se guardan automáticamente")
        print("="*60)
        
        self.app.run_server(debug=debug, port=port, host=host)

if __name__ == "__main__":
    try:
        # Crear y ejecutar la herramienta
        tool = AdvancedAnnotationTool()
        tool.run(debug=False, port=8050)
    except Exception as e:
        print(f"❌ Error iniciando la aplicación: {e}")
        print("💡 Asegúrate de que:")
        print("  - El directorio dataset_cruce_3 existe")
        print("  - Hay imágenes en dataset_cruce_3/train/images/")
        print("  - Las dependencias están instaladas (pip install -r requirements_annotation_tool.txt)")
