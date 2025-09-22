"""
Componente de Herramienta de Anotación - Integrado en AutoDistill Suite
Herramienta de corrección de etiquetado similar a CVAT, convertida en componente reutilizable
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

class AnnotationToolComponent:
    def __init__(self, app=None):
        self.app = app
        self.dataset_path = None
        self.images_path = None
        self.labels_path = None
        self.classes = ["vehículo"]  # Default, se puede configurar
        self.current_image_index = 0
        self.image_files = []
        
        # Solo configurar callbacks si se pasa una app
        if self.app:
            self.setup_callbacks()
    
    def set_dataset_path(self, dataset_path):
        """Configurar la ruta del dataset"""
        self.dataset_path = dataset_path
        self.images_path = os.path.join(dataset_path, "train", "images")
        self.labels_path = os.path.join(dataset_path, "train", "labels")
        
        # Verificar que los directorios existen
        if not os.path.exists(self.images_path):
            raise FileNotFoundError(f"Directorio de imágenes no encontrado: {self.images_path}")
        
        self.image_files = sorted([f for f in os.listdir(self.images_path) 
                                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        if not self.image_files:
            raise FileNotFoundError(f"No se encontraron imágenes en: {self.images_path}")
        
        self.current_image_index = 0
    
    def get_layout(self, dataset_path=None):
        """Obtener el layout del componente"""
        if dataset_path:
            try:
                self.set_dataset_path(dataset_path)
                dataset_info = f"📁 Dataset: {self.dataset_path} • 🖼️ {len(self.image_files)} imágenes"
                dataset_alert = None
            except Exception as e:
                dataset_info = f"❌ Error: {str(e)}"
                dataset_alert = dbc.Alert([
                    html.H5("⚠️ Error al cargar dataset", className="alert-heading"),
                    html.P(f"No se pudo acceder al dataset: {str(e)}"),
                    html.P("Por favor selecciona un dataset válido desde la gestión de archivos.", className="mb-0")
                ], color="danger")
        else:
            dataset_info = "❌ No hay dataset seleccionado"
            dataset_alert = dbc.Alert([
                html.H5("📁 Dataset no seleccionado", className="alert-heading"),
                html.P("Para usar la herramienta de etiquetado necesitas seleccionar un dataset primero."),
                dbc.Button("Ir a Gestión de Archivos", id="go-to-files", color="primary", size="sm")
            ], color="info")
        
        layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("🏷️ Herramienta de Corrección de Etiquetado", 
                           className="text-center mb-2", 
                           style={"color": "#00d4aa", "font-weight": "bold"}),
                    html.P(dataset_info, className="text-center text-muted mb-3"),
                    html.Hr(style={"border-color": "#495057"})
                ])
            ]),
            
            # Alert si hay error
            dataset_alert if dataset_alert else html.Div(),
            
            # Contenido principal (solo si hay dataset válido)
            html.Div(
                id="annotation-tool-content",
                children=self._get_annotation_interface() if dataset_path and not dataset_alert else html.Div(),
                style={"display": "block" if dataset_path and not dataset_alert else "none"}
            )
            
        ], fluid=True, className="py-3")
        
        return layout
    
    def _get_annotation_interface(self):
        """Obtener la interfaz principal de anotación"""
        return [
            # Stores para mantener el estado
            dcc.Store(id='current-annotations', data=[]),
            dcc.Store(id='current-image-data', data={}),
            dcc.Store(id='image-dimensions', data={}),
            dcc.Store(id='keyboard-trigger', data=0),
            
            # Panel de control
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("📂 Navegación:", className="fw-bold mb-2", 
                                     style={"color": "#00d4aa"}),
                            dbc.ButtonGroup([
                                dbc.Button("◀◀", id="first-button", color="outline-info", size="sm"),
                                dbc.Button("◀", id="prev-button", color="info", size="sm"),
                                dbc.Button("▶", id="next-button", color="info", size="sm"),
                                dbc.Button("▶▶", id="last-button", color="outline-info", size="sm"),
                            ], className="w-100"),
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("📊 Estado:", className="fw-bold mb-2", style={"color": "#00d4aa"}),
                            html.P(id="image-counter", className="text-center mb-0 fs-6 fw-bold",
                                  style={"color": "#adb5bd", "background": "rgba(0,212,170,0.1)", 
                                         "padding": "0.5rem", "border-radius": "0.5rem"})
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("🛠️ Herramientas:", className="fw-bold mb-2", style={"color": "#00d4aa"}),
                            dbc.Button("🗑️ Eliminar Frame", id="delete-frame-button", 
                                     color="danger", size="sm", className="w-100"),
                        ], width=3),
                        
                        dbc.Col([
                            html.Label("⌨️ Atajos:", className="fw-bold mb-2", style={"color": "#00d4aa"}),
                            html.Small("F=Siguiente • D=Anterior", className="text-muted"),
                            html.Br(),
                            html.Small("💾 Guardado automático", className="text-success")
                        ], width=3)
                    ])
                ])
            ], className="mb-3", 
               style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                      "border": "1px solid #495057"}),
            
            # Área principal de contenido
            dbc.Row([
                # Visor de imágenes
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📸 Visor de Imágenes", className="mb-0", style={"color": "#00d4aa"}),
                            dbc.Badge(id="annotation-count-badge", color="info", className="ms-2")
                        ], style={"background": "#2d3748", "border-bottom": "1px solid #495057"}),
                        dbc.CardBody([
                            dcc.Graph(
                                id="image-graph",
                                config={
                                    'displayModeBar': True,
                                    'modeBarButtonsToRemove': [
                                        'pan2d', 'select2d', 'lasso2d', 'resetScale2d',
                                        'zoomIn2d', 'zoomOut2d', 'autoScale2d'
                                    ],
                                    'displaylogo': False
                                },
                                style={'height': '60vh'}
                            ),
                            html.Div(id="mouse-coords", className="text-muted small mt-2")
                        ], style={'background': '#1a1a1a'})
                    ], style={"background": "#1a1a1a", "border": "1px solid #495057"})
                ], width=8),
                
                # Panel lateral
                dbc.Col([
                    # Lista de anotaciones
                    dbc.Card([
                        dbc.CardHeader("🏷️ Anotaciones", 
                                     style={"background": "#2d3748", "color": "#00d4aa", "font-weight": "bold"}),
                        dbc.CardBody([
                            html.Div(id="annotations-list", style={'max-height': '300px', 'overflow-y': 'auto'})
                        ], style={"background": "#1a1a1a"})
                    ], className="mb-3", style={"background": "#1a1a1a", "border": "1px solid #495057"}),
                    
                    # Configuración
                    dbc.Card([
                        dbc.CardHeader("🎨 Configuración", 
                                     style={"background": "#2d3748", "color": "#00d4aa", "font-weight": "bold"}),
                        dbc.CardBody([
                            html.Label("Clase:", className="mb-2", style={"color": "#00d4aa"}),
                            dbc.Select(
                                id="class-selector",
                                options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                                value=0,
                                size="sm",
                                className="mb-3"
                            ),
                            html.Label("Opacidad:", className="mb-2", style={"color": "#00d4aa"}),
                            dcc.Slider(
                                id="opacity-slider",
                                min=0.1, max=1.0, value=0.3, step=0.1,
                                marks={i/10: str(i/10) for i in range(1, 11)},
                                className="mb-3"
                            ),
                            dbc.Checklist(
                                options=[
                                    {"label": " Mostrar IDs", "value": "show_ids"},
                                    {"label": " Coordenadas", "value": "show_coords"},
                                ],
                                value=["show_ids"],
                                id="display-options"
                            )
                        ], style={"background": "#1a1a1a"})
                    ], style={"background": "#1a1a1a", "border": "1px solid #495057"})
                ], width=4)
            ]),
            
            # Toast para notificaciones
            dbc.Toast(
                id="notification-toast",
                header="Notificación",
                is_open=False,
                dismissable=True,
                duration=3000,
                style={"position": "fixed", "top": 66, "right": 10, "width": 350}
            ),
            
            # Modal de confirmación
            dbc.Modal([
                dbc.ModalHeader("⚠️ Confirmar Eliminación"),
                dbc.ModalBody("¿Estás seguro de que quieres eliminar este frame?"),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-delete", color="secondary"),
                    dbc.Button("Eliminar", id="confirm-delete", color="danger")
                ])
            ], id="delete-modal", is_open=False)
        ]
    
    # Métodos auxiliares de la herramienta original
    def load_image_annotations(self, image_filename):
        """Cargar anotaciones para una imagen específica"""
        if not self.labels_path:
            return []
            
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
                        except (ValueError, IndexError):
                            continue
        
        return annotations
    
    def save_annotations(self, image_filename, annotations):
        """Guardar anotaciones en formato YOLO"""
        if not self.labels_path:
            return
            
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        if not annotations:
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
        x_min = max(0, min(x_min, img_width))
        y_min = max(0, min(y_min, img_height))
        x_max = max(0, min(x_max, img_width))
        y_max = max(0, min(y_max, img_height))
        
        if x_max <= x_min:
            x_max = x_min + 1
        if y_max <= y_min:
            y_max = y_min + 1
        
        x_center = ((x_min + x_max) / 2) / img_width
        y_center = ((y_min + y_max) / 2) / img_height
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height
        
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
    
    def create_figure_with_annotations(self, image_filename, annotations, opacity=0.3, show_ids=True, show_coords=False):
        """Crear figura de Plotly con imagen y anotaciones"""
        if not self.images_path:
            fig = go.Figure()
            fig.update_layout(title="❌ No hay dataset configurado")
            return fig, {'width': 800, 'height': 600}
            
        image_path = os.path.join(self.images_path, image_filename)
        
        if not os.path.exists(image_path):
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
        
        # Agregar imagen como fondo
        img_base64 = self.get_image_as_base64(image_path)
        fig.add_layout_image(
            dict(
                source=img_base64,
                xref="x", yref="y",
                x=0, y=img_height,
                sizex=img_width, sizey=img_height,
                sizing="stretch", opacity=1, layer="below"
            )
        )
        
        # Agregar bounding boxes
        colors = ['#00d4aa', '#ff6b6b', '#4ecdc4', '#45b7d1', '#feca57', '#ff9ff3', '#54a0ff']
        shapes = []
        
        for ann in annotations:
            x_min, y_min, x_max, y_max = self.yolo_to_pixel_coords(ann, img_width, img_height)
            color = colors[ann['class_id'] % len(colors)]
            
            # Invertir Y para Plotly
            y_min_plot = img_height - y_max
            y_max_plot = img_height - y_min
            
            # Color con transparencia
            color_rgb = [int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
            fill_color = f"rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]},{opacity})"
            
            shape = dict(
                type="rect",
                x0=x_min, y0=y_min_plot,
                x1=x_max, y1=y_max_plot,
                line=dict(color=color, width=3),
                fillcolor=fill_color,
                editable=True,
                name=f"bbox_{ann['id']}"
            )
            shapes.append(shape)
            
            # Etiqueta
            if show_ids or show_coords:
                label_parts = []
                if show_ids:
                    label_parts.append(f"ID:{ann['id']}")
                label_parts.append(ann['class_name'])
                if show_coords:
                    label_parts.append(f"({ann['x_center']:.3f},{ann['y_center']:.3f})")
                
                fig.add_annotation(
                    x=x_min, y=y_max_plot,
                    text=" | ".join(label_parts),
                    showarrow=False,
                    bgcolor=color, bordercolor=color, borderwidth=2,
                    font=dict(color="white", size=11),
                    xanchor="left", yanchor="bottom"
                )
        
        # Configurar figura
        fig.update_layout(
            title=f"📸 {image_filename} - ✏️ Dibuja rectángulos para crear anotaciones",
            showlegend=False,
            margin=dict(l=0, r=0, t=60, b=0),
            dragmode="drawrect",
            newshape=dict(line=dict(color="#00d4aa", width=3), fillcolor="rgba(0,212,170,0.2)"),
            plot_bgcolor='#1a1a1a', paper_bgcolor='#1a1a1a',
            shapes=shapes,
            xaxis=dict(range=[0, img_width], showgrid=False, showticklabels=False, 
                      zeroline=False, fixedrange=True),
            yaxis=dict(range=[0, img_height], showgrid=False, showticklabels=False, 
                      zeroline=False, scaleanchor="x", scaleratio=1, fixedrange=True)
        )
        
        return fig, {'width': img_width, 'height': img_height}
    
    def setup_callbacks(self):
        """Configurar callbacks (implementación simplificada para el ejemplo)"""
        # Aquí irían todos los callbacks de la herramienta original
        # Por ahora, implementamos solo los básicos para que funcione la navegación
        
        # JavaScript para eventos de teclado
        clientside_callback(
            """
            function(n) {
                document.addEventListener('keydown', function(event) {
                    if (event.key === 'f' || event.key === 'F') {
                        const nextBtn = document.getElementById('next-button');
                        if (nextBtn) nextBtn.click();
                        event.preventDefault();
                    } else if (event.key === 'd' || event.key === 'D') {
                        const prevBtn = document.getElementById('prev-button');
                        if (prevBtn) prevBtn.click();
                        event.preventDefault();
                    }
                });
                return n;
            }
            """,
            Output('keyboard-trigger', 'data'),
            [Input('image-graph', 'id')]
        )