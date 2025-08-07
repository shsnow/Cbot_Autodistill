"""
Herramienta de Corrección de Etiquetado - Similar a CVAT
Permite editar anotaciones YOLO de manera interactiva
"""

import dash
from dash import dcc, html, callback, Input, Output, State, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
import json
import base64
from PIL import Image
import io

class AnnotationTool:
    def __init__(self, dataset_path="dataset_cruce_3"):
        self.dataset_path = dataset_path
        self.images_path = os.path.join(dataset_path, "train", "images")
        self.labels_path = os.path.join(dataset_path, "train", "labels")
        self.classes = ["vehícule"]  # Basado en tu ontología
        self.current_image_index = 0
        self.image_files = sorted([f for f in os.listdir(self.images_path) if f.endswith('.jpg')])
        
        # Estado para tracking de cambios
        self.unsaved_changes = {}
        
        # Configurar la app Dash
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.setup_layout()
        self.setup_callbacks()
    
    def load_image_annotations(self, image_filename):
        """Cargar anotaciones para una imagen específica"""
        label_filename = image_filename.replace('.jpg', '.txt')
        label_path = os.path.join(self.labels_path, label_filename)
        
        annotations = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line_idx, line in enumerate(f.readlines()):
                    line = line.strip()
                    if line:
                        parts = line.split()
                        class_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        annotations.append({
                            'id': line_idx,
                            'class_id': class_id,
                            'class_name': self.classes[class_id],
                            'x_center': x_center,
                            'y_center': y_center,
                            'width': width,
                            'height': height
                        })
        
        return annotations
    
    def save_annotations(self, image_filename, annotations):
        """Guardar anotaciones en formato YOLO"""
        label_filename = image_filename.replace('.jpg', '.txt')
        label_path = os.path.join(self.labels_path, label_filename)
        
        with open(label_path, 'w') as f:
            for ann in annotations:
                line = f"{ann['class_id']} {ann['x_center']:.5f} {ann['y_center']:.5f} {ann['width']:.5f} {ann['height']:.5f}\n"
                f.write(line)
    
    def yolo_to_pixel_coords(self, annotation, img_width, img_height):
        """Convertir coordenadas YOLO normalizadas a píxeles"""
        x_center = annotation['x_center'] * img_width
        y_center = annotation['y_center'] * img_height
        width = annotation['width'] * img_width
        height = annotation['height'] * img_height
        
        x_min = x_center - width / 2
        y_min = y_center - height / 2
        x_max = x_center + width / 2
        y_max = y_center + height / 2
        
        return x_min, y_min, x_max, y_max
    
    def pixel_to_yolo_coords(self, x_min, y_min, x_max, y_max, img_width, img_height):
        """Convertir coordenadas de píxeles a formato YOLO normalizado"""
        x_center = ((x_min + x_max) / 2) / img_width
        y_center = ((y_min + y_max) / 2) / img_height
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height
        
        return x_center, y_center, width, height
    
    def setup_layout(self):
        """Configurar el layout de la aplicación"""
        self.app.layout = dbc.Container([
            dcc.Store(id='current-annotations', data=[]),
            dcc.Store(id='current-image-data', data={}),
            dcc.Store(id='image-dimensions', data={}),
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🔧 Herramienta de Corrección de Etiquetado", 
                           className="text-center mb-4 text-primary"),
                    html.Hr()
                ])
            ]),
            
            # Controls
            dbc.Row([
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("◀ Anterior", id="prev-button", color="secondary", size="sm"),
                        dbc.Button("Siguiente ▶", id="next-button", color="secondary", size="sm"),
                    ]),
                ], width=3),
                
                dbc.Col([
                    html.P(id="image-counter", className="text-center fw-bold")
                ], width=3),
                
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("➕ Nueva Caja", id="add-box-button", color="success", size="sm"),
                        dbc.Button("🗑️ Eliminar Frame", id="delete-frame-button", color="danger", size="sm"),
                    ]),
                ], width=3),
                
                dbc.Col([
                    dbc.Button("💾 Guardar", id="save-button", color="primary", size="sm"),
                    html.Span(id="save-status", className="ms-2")
                ], width=3)
            ], className="mb-3"),
            
            # Main content
            dbc.Row([
                # Image and annotations
                dbc.Col([
                    dcc.Graph(
                        id="image-graph",
                        config={
                            'displayModeBar': True,
                            'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'resetScale2d'],
                            'displaylogo': False
                        },
                        style={'height': '70vh'}
                    )
                ], width=9),
                
                # Sidebar with annotation list
                dbc.Col([
                    html.H5("🏷️ Anotaciones", className="mb-3"),
                    html.Div(id="annotations-list"),
                    html.Hr(),
                    html.H6("➕ Agregar Clase:"),
                    dbc.Select(
                        id="class-selector",
                        options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                        value=0,
                        size="sm"
                    ),
                ], width=3)
            ]),
            
            # Tooltips and modals
            dbc.Modal([
                dbc.ModalHeader("⚠️ Confirmar"),
                dbc.ModalBody("¿Estás seguro de que quieres eliminar este frame? Esta acción no se puede deshacer."),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-delete", color="secondary"),
                    dbc.Button("Eliminar", id="confirm-delete", color="danger")
                ])
            ], id="delete-modal", is_open=False),
            
        ], fluid=True)
    
    def create_figure_with_annotations(self, image_filename, annotations):
        """Crear figura de Plotly con imagen y anotaciones"""
        image_path = os.path.join(self.images_path, image_filename)
        
        # Cargar imagen
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # Crear figura
        fig = go.Figure()
        
        # Agregar imagen como fondo
        fig.add_layout_image(
            dict(
                source=img,
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
        
        # Agregar bounding boxes
        colors = px.colors.qualitative.Set1
        for i, ann in enumerate(annotations):
            x_min, y_min, x_max, y_max = self.yolo_to_pixel_coords(ann, img_width, img_height)
            color = colors[ann['class_id'] % len(colors)]
            
            # Rectángulo del bounding box
            fig.add_shape(
                type="rect",
                x0=x_min, y0=img_height - y_max,
                x1=x_max, y1=img_height - y_min,
                line=dict(color=color, width=2),
                fillcolor=f"rgba{tuple(list(px.colors.hex_to_rgb(color)) + [0.2])}",
                name=f"bbox_{ann['id']}"
            )
            
            # Etiqueta de clase
            fig.add_annotation(
                x=x_min,
                y=img_height - y_min,
                text=f"{ann['class_name']} ({ann['id']})",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=color,
                ax=20,
                ay=-30,
                bgcolor=color,
                bordercolor=color,
                font=dict(color="white", size=10)
            )
        
        # Configurar ejes
        fig.update_xaxes(
            range=[0, img_width],
            showgrid=False,
            showticklabels=False,
            zeroline=False
        )
        
        fig.update_yaxes(
            range=[0, img_height],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1
        )
        
        fig.update_layout(
            title=f"📸 {image_filename}",
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            dragmode="drawrect",
            newshape=dict(
                line=dict(color="red", width=2),
                fillcolor="rgba(255,0,0,0.2)"
            )
        )
        
        return fig, {'width': img_width, 'height': img_height}
    
    def setup_callbacks(self):
        """Configurar callbacks de Dash"""
        
        @self.app.callback(
            [Output('image-graph', 'figure'),
             Output('current-annotations', 'data'),
             Output('image-counter', 'children'),
             Output('image-dimensions', 'data'),
             Output('current-image-data', 'data')],
            [Input('next-button', 'n_clicks'),
             Input('prev-button', 'n_clicks')],
            [State('current-annotations', 'data')]
        )
        def navigate_images(next_clicks, prev_clicks, current_annotations):
            """Navegar entre imágenes"""
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if button_id == 'next-button' and next_clicks:
                    self.current_image_index = min(self.current_image_index + 1, len(self.image_files) - 1)
                elif button_id == 'prev-button' and prev_clicks:
                    self.current_image_index = max(self.current_image_index - 1, 0)
            
            current_image = self.image_files[self.current_image_index]
            annotations = self.load_image_annotations(current_image)
            fig, img_dims = self.create_figure_with_annotations(current_image, annotations)
            
            counter_text = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
            
            return fig, annotations, counter_text, img_dims, {'filename': current_image}
        
        @self.app.callback(
            Output('annotations-list', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_annotations_list(annotations):
            """Actualizar lista de anotaciones en el sidebar"""
            if not annotations:
                return html.P("No hay anotaciones", className="text-muted")
            
            items = []
            for ann in annotations:
                items.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.H6(f"{ann['class_name']}", className="card-title"),
                            html.Small(f"ID: {ann['id']}", className="text-muted"),
                            html.Br(),
                            html.Small(f"Centro: ({ann['x_center']:.3f}, {ann['y_center']:.3f})"),
                            html.Br(),
                            html.Small(f"Tamaño: {ann['width']:.3f} × {ann['height']:.3f}"),
                            html.Hr(className="my-2"),
                            dbc.ButtonGroup([
                                dbc.Button("📝", id={"type": "edit-btn", "index": ann['id']}, 
                                         size="sm", color="warning"),
                                dbc.Button("🗑️", id={"type": "delete-btn", "index": ann['id']}, 
                                         size="sm", color="danger")
                            ], size="sm")
                        ])
                    ], className="mb-2")
                )
            
            return items
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True)],
            [Input('image-graph', 'relayoutData')],
            [State('current-annotations', 'data'),
             State('image-dimensions', 'data'),
             State('current-image-data', 'data'),
             State('class-selector', 'value')],
            prevent_initial_call=True
        )
        def handle_shape_drawing(relayout_data, annotations, img_dims, image_data, selected_class):
            """Manejar el dibujo de nuevas formas/bounding boxes"""
            if not relayout_data or not img_dims:
                return annotations, dash.no_update
            
            # Detectar si se dibujó una nueva forma
            if 'shapes' in relayout_data:
                shapes = relayout_data['shapes']
                if shapes and len(shapes) > 0:
                    # Obtener la última forma dibujada
                    new_shape = shapes[-1]
                    
                    if new_shape['type'] == 'rect':
                        # Convertir coordenadas de píxeles a YOLO
                        x0, y0 = new_shape['x0'], img_dims['height'] - new_shape['y1']
                        x1, y1 = new_shape['x1'], img_dims['height'] - new_shape['y0']
                        
                        x_center, y_center, width, height = self.pixel_to_yolo_coords(
                            x0, y0, x1, y1, img_dims['width'], img_dims['height']
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
                        
                        annotations.append(new_annotation)
                        
                        # Regenerar figura con todas las anotaciones
                        fig, _ = self.create_figure_with_annotations(image_data['filename'], annotations)
                        
                        return annotations, fig
            
            return annotations, dash.no_update
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True)],
            [Input({"type": "delete-btn", "index": ALL}, "n_clicks")],
            [State('current-annotations', 'data'),
             State('current-image-data', 'data')],
            prevent_initial_call=True
        )
        def delete_annotation(delete_clicks, annotations, image_data):
            """Eliminar anotación específica"""
            if not any(delete_clicks) or not ctx.triggered:
                return annotations, dash.no_update
            
            # Obtener el ID de la anotación a eliminar
            button_id = ctx.triggered[0]['prop_id']
            if 'index' in button_id:
                import re
                match = re.search(r'"index":(\d+)', button_id)
                if match:
                    delete_id = int(match.group(1))
                    
                    # Filtrar anotaciones
                    annotations = [ann for ann in annotations if ann['id'] != delete_id]
                    
                    # Reindexar IDs
                    for i, ann in enumerate(annotations):
                        ann['id'] = i
                    
                    # Regenerar figura
                    fig, _ = self.create_figure_with_annotations(image_data['filename'], annotations)
                    
                    return annotations, fig
            
            return annotations, dash.no_update
        
        @self.app.callback(
            Output('save-status', 'children'),
            [Input('save-button', 'n_clicks')],
            [State('current-annotations', 'data'),
             State('current-image-data', 'data')]
        )
        def save_current_annotations(save_clicks, annotations, image_data):
            """Guardar anotaciones actuales"""
            if save_clicks and image_data:
                self.save_annotations(image_data['filename'], annotations)
                return dbc.Badge("✓ Guardado", color="success", className="ms-2")
            return ""
        
        @self.app.callback(
            [Output('delete-modal', 'is_open'),
             Output('current-image-data', 'data', allow_duplicate=True)],
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
                    return True, image_data
                elif button_id == 'confirm-delete' and confirm_clicks:
                    if image_data and 'filename' in image_data:
                        # Eliminar archivos de imagen y etiqueta
                        img_path = os.path.join(self.images_path, image_data['filename'])
                        label_path = os.path.join(self.labels_path, image_data['filename'].replace('.jpg', '.txt'))
                        
                        if os.path.exists(img_path):
                            os.remove(img_path)
                        if os.path.exists(label_path):
                            os.remove(label_path)
                        
                        # Actualizar lista de archivos
                        self.image_files = sorted([f for f in os.listdir(self.images_path) if f.endswith('.jpg')])
                        
                        # Ajustar índice actual
                        if self.current_image_index >= len(self.image_files):
                            self.current_image_index = max(0, len(self.image_files) - 1)
                    
                    return False, image_data
                elif button_id == 'cancel-delete':
                    return False, image_data
            
            return is_open, image_data
    
    def run(self, debug=True, port=8050):
        """Ejecutar la aplicación"""
        print(f"🚀 Iniciando herramienta de anotación...")
        print(f"📁 Dataset: {self.dataset_path}")
        print(f"🖼️ Imágenes encontradas: {len(self.image_files)}")
        print(f"🌐 Abriendo en: http://localhost:{port}")
        
        self.app.run_server(debug=debug, port=port, host='0.0.0.0')

if __name__ == "__main__":
    # Crear y ejecutar la herramienta
    tool = AnnotationTool()
    tool.run()
