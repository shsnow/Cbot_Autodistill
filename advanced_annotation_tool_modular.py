"""
Herramienta Avanzada de Corrección de Etiquetado - Similar a CVAT
Versión modular con funcionalidades separadas
"""

import dash
from dash import dcc, html, callback, Input, Output, State, ctx, ALL, no_update, clientside_callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import json
import argparse
import os
import re

# Importar módulos locales
from utils import (
    ConfigLoader, AnnotationManager, CoordinateConverter, 
    UndoManager, FigureGenerator, CallbackManager
)


class AdvancedAnnotationTool:
    """Herramienta avanzada para edición de anotaciones YOLO"""
    
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
        self.classes_yaml = os.path.join(dataset_path, "data.yaml")
        self.images_path = os.path.join(dataset_path, "images")
        self.labels_path = os.path.join(dataset_path, "annotations")
        
        # Inicializar módulos
        self._initialize_modules(self.classes_yaml)
        
        # Variables de estado
        self.current_image_index = 0
        self.selected_annotation_id = None
        
        # Verificar directorios
        self._validate_directories()
        
        # Obtener archivos de imagen
        self._load_image_files()
        
        # Configurar la app Dash
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
        self.setup_layout()
        self.setup_callbacks()
    
    def _initialize_modules(self, classes_yaml):
        """Inicializar todos los módulos necesarios"""
        # Cargar configuración
        self.config_loader = ConfigLoader(classes_yaml)
        self.classes = self.config_loader.get_classes()
        self.class_colors = self.config_loader.get_colors(len(self.classes))
        
        # Inicializar managers
        self.annotation_manager = AnnotationManager(self.labels_path, self.classes)
        self.undo_manager = UndoManager(max_steps=20)
        self.figure_generator = FigureGenerator(self.images_path, self.class_colors)
        self.callback_manager = CallbackManager(
            self.annotation_manager, self.undo_manager, 
            self.figure_generator, self.classes
        )
        
        # Converter utility
        self.converter = CoordinateConverter()
    
    def _validate_directories(self):
        """Validar que los directorios necesarios existen"""
        if not os.path.exists(self.images_path):
            raise FileNotFoundError(f"Directorio de imágenes no encontrado: {self.images_path}")
        
        # Crear directorio de labels si no existe
        if not os.path.exists(self.labels_path):
            os.makedirs(self.labels_path)
            print(f"✅ Creado directorio de etiquetas: {self.labels_path}")
    
    def _load_image_files(self):
        """Cargar lista de archivos de imagen"""
        self.image_files = sorted([
            f for f in os.listdir(self.images_path) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if not self.image_files:
            raise FileNotFoundError(f"No se encontraron imágenes en: {self.images_path}")
    
    def setup_layout(self):
        """Configurar el layout de la aplicación"""
        self.app.layout = dbc.Container([
            # Stores para mantener el estado
            dcc.Store(id='current-annotations', data=[]),
            dcc.Store(id='current-image-data', data={}),
            dcc.Store(id='image-dimensions', data={}),
            dcc.Store(id='selected-annotation', data=None),
            dcc.Store(id='keyboard-trigger', data=0),
            
            # Elemento invisible para el listener de teclado
            html.Div(id="keyboard-listener", style={"display": "none"}),
            
            # Header
            self._create_header(),
            
            # Control Panel
            self._create_control_panel(),
            
            # Main content area
            self._create_main_content(),
            
            # Modals
            self._create_modals(),
            
            # Toast para notificaciones
            self._create_toast(),
            
        ], fluid=True, style={
            'padding': '1rem', 
            'background': 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)', 
            'min-height': '100vh'
        })
    
    def _create_header(self):
        """Crear el header de la aplicación"""
        return dbc.Row([
            dbc.Col([
                html.H1("🔧 Cbot", 
                       className="text-center mb-3", 
                       style={"color": "#00d4aa", "font-weight": "bold", 
                             "font-family": "Arial Black", 
                             "text-shadow": "0 0 10px rgba(0,212,170,0.5)"}),
                html.P("Edita anotaciones YOLO de manera interactiva - Similar a CVAT",
                       className="text-center", 
                       style={"color": "#adb5bd", "font-size": "1.1rem", 
                             "margin-bottom": "2rem"}),
                html.Hr(style={"border-color": "#495057", "border-width": "2px"})
            ])
        ])
    
    def _create_control_panel(self):
        """Crear el panel de control"""
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # Navegación
                    dbc.Col([
                        html.Label("📂 Navegación:", className="fw-bold mb-2", 
                                 style={"color": "#00d4aa", "font-family": "Arial Black"}),
                        dbc.ButtonGroup([
                            dbc.Button("◀◀ Primero", id="first-button", color="outline-info", 
                                     size="sm", className="shadow-sm"),
                            dbc.Button("◀ Anterior", id="prev-button", color="info", 
                                     size="sm", className="shadow-sm"),
                            dbc.Button("Siguiente ▶", id="next-button", color="info", 
                                     size="sm", className="shadow-sm"),
                            dbc.Button("Último ▶▶", id="last-button", color="outline-info", 
                                     size="sm", className="shadow-sm"),
                        ], className="w-100"),
                    ], width=3),
                    
                    # Estado
                    dbc.Col([
                        html.Label("📊 Estado:", className="fw-bold mb-2", 
                                 style={"color": "#00d4aa", "font-family": "Arial Black"}),
                        html.P(id="image-counter", className="text-center mb-0 fs-6 fw-bold",
                              style={"color": "#adb5bd", "background": "rgba(0,212,170,0.1)", 
                                    "padding": "0.5rem", "border-radius": "0.5rem"})
                    ], width=3),
                    
                    # Herramientas
                    dbc.Col([
                        html.Label("🛠️ Herramientas:", className="fw-bold mb-2", 
                                 style={"color": "#00d4aa", "font-family": "Arial Black"}),
                        dbc.ButtonGroup([
                            dbc.Button("↶ Deshacer", id="undo-button", color="warning", 
                                     size="sm", className="shadow-sm", title="Ctrl+Z"),
                            dbc.Button("🗑️ Seleccionada", id="delete-selected-button", 
                                     color="danger", size="sm", className="shadow-sm", 
                                     title="Eliminar anotación seleccionada - Supr"),
                        ], className="w-100 mb-1"),
                        dbc.ButtonGroup([
                            dbc.Button("🗑️ Última", id="delete-last-button", 
                                     color="outline-danger", size="sm", className="shadow-sm", 
                                     title="Eliminar última anotación"),
                        ], className="w-100 mb-1"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Input(
                                    id="delete-id-input", 
                                    type="number", 
                                    placeholder="ID", 
                                    size="sm",
                                    min=0,
                                    style={"width": "60px"}
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Button("🗑️ ID", id="delete-by-id-button", 
                                         color="outline-danger", size="sm", className="shadow-sm",
                                         title="Eliminar por ID")
                            ], width=8)
                        ], className="w-100 mb-1"),
                        dbc.ButtonGroup([
                            dbc.Button("🗑️ Eliminar Frame", id="delete-frame-button", 
                                     color="danger", size="sm", className="shadow-sm"),
                        ], className="w-100"),
                        html.Small("✏️ Dibuja para crear • 🎯 Clic para seleccionar • 🗑️ Supr para eliminar", 
                                 className="text-muted mt-1")
                    ], width=3),
                    
                    # Acciones
                    dbc.Col([
                        html.Label("💾 Acciones:", className="fw-bold mb-2", 
                                 style={"color": "#00d4aa", "font-family": "Arial Black"}),
                        dbc.ButtonGroup([
                            dbc.Button("🔄 Recargar", id="reload-button", color="info", 
                                     size="sm", className="shadow-sm"),
                        ]),
                        html.Small("⌨️ F=Siguiente • D=Anterior • Ctrl+Z=Deshacer • Supr=Eliminar", 
                                 className="text-muted mt-1")
                    ], width=3)
                ])
            ])
        ], className="mb-3", style={
            "background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
            "border": "1px solid #495057", "border-radius": "1rem"
        })
    
    def _create_main_content(self):
        """Crear el contenido principal"""
        return dbc.Row([
            # Visor de imágenes
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
                                    'format': 'png', 'filename': 'anotacion',
                                    'height': 500, 'width': 700, 'scale': 1
                                }
                            },
                            style={'height': '65vh', 'width': '100%'}
                        ),
                        html.Div(id="mouse-coords", className="text-muted small mt-2")
                    ], style={'padding': '0.5rem', 'background': '#1a1a1a', 
                             'border-radius': '0 0 1rem 1rem'})
                ], style={"background": "#1a1a1a", "border": "1px solid #495057", 
                         "border-radius": "1rem"})
            ], width=8),
            
            # Sidebar con controles
            dbc.Col([
                self._create_annotations_list(),
                self._create_configuration_panel(),
                self._create_statistics_panel()
            ], width=4)
        ])
    
    def _create_annotations_list(self):
        """Crear la lista de anotaciones"""
        return dbc.Card([
            dbc.CardHeader("🏷️ Lista de Anotaciones", 
                         style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                               "color": "#00d4aa", "font-weight": "bold", 
                               "border-bottom": "1px solid #495057"}),
            dbc.CardBody([
                html.Div(id="annotations-list", style={'max-height': '300px', 'overflow-y': 'auto'})
            ], style={"background": "#1a1a1a"})
        ], className="mb-3", style={"background": "#1a1a1a", "border": "1px solid #495057", 
                                   "border-radius": "1rem"})
    
    def _create_configuration_panel(self):
        """Crear el panel de configuración"""
        return dbc.Card([
            dbc.CardHeader("🎨 Configuración", 
                         style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                               "color": "#00d4aa", "font-weight": "bold", 
                               "border-bottom": "1px solid #495057"}),
            dbc.CardBody([
                html.Label("Clase para nuevas anotaciones:", className="mb-2", 
                         style={"color": "#00d4aa", "font-weight": "bold"}),
                dbc.Select(
                    id="class-selector",
                    options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                    value=0, size="sm", className="mb-3"
                ),
                
                # Sección para anotación seleccionada - MÁS PROMINENTE
                html.Hr(className="my-3", style={"border-color": "#ffd700", "border-width": "3px"}),
                dbc.Alert([
                    html.H5("🎯 CAMBIAR CLASE DE ANOTACIÓN SELECCIONADA", 
                           className="mb-3", style={"color": "#ffd700", "font-weight": "bold", "text-align": "center"}),
                    
                    # Estado de selección prominente
                    dbc.Alert(id="selected-info", color="info", className="mb-3 text-center", 
                             style={"font-size": "1.1rem", "font-weight": "bold", "border": "2px solid #17a2b8"}),
                    
                    # Controles más grandes y visibles
                    dbc.Row([
                        dbc.Col([
                            html.Label("🔄 Nueva clase:", className="mb-2", 
                                     style={"color": "#ffd700", "font-weight": "bold", "font-size": "1.1rem"}),
                            dbc.Select(
                                id="selected-class-selector",
                                options=[{"label": f"🏷️ {cls}", "value": i} for i, cls in enumerate(self.classes)],
                                value=0, size="lg", disabled=True,
                                style={"font-weight": "bold", "font-size": "1rem"}
                            )
                        ], width=7),
                        dbc.Col([
                            html.Label("🚀 Acción:", className="mb-2", 
                                     style={"color": "#ffd700", "font-weight": "bold", "font-size": "1.1rem"}),
                            dbc.Button("✅ CAMBIAR AHORA", id="change-class-button", color="success", 
                                     size="lg", disabled=True, 
                                     title="Cambiar clase de la anotación seleccionada (selecciona una anotación primero)",
                                     style={"font-weight": "bold", "width": "100%", "opacity": "0.6", "font-size": "1rem"})
                        ], width=5)
                    ], className="mb-3"),
                    
                    # Instrucciones mejoradas
                    dbc.Alert([
                        html.H6("📋 Múltiples formas de seleccionar:", className="mb-2", style={"color": "#856404"}),
                        html.Ol([
                            html.Li("🖱️ Haz clic en cualquier parte de una bounding box en la imagen"),
                            html.Li("🎯 Presiona el botón '🎯' en la lista de anotaciones (panel derecho)"),
                            html.Li("✏️ Arrastra/edita una bounding box (se selecciona automáticamente)"),
                            html.Li("👀 Verás que se resalta en amarillo cuando esté seleccionada"),
                            html.Li("🔄 Elige la nueva clase en el selector de arriba"),
                            html.Li("✅ Presiona 'CAMBIAR AHORA' para aplicar"),
                            html.Li("💾 El cambio se guarda automáticamente")
                        ], style={"color": "#856404", "margin-bottom": "0"})
                    ], color="warning", style={"background": "rgba(255,193,7,0.1)", "border": "1px solid #ffc107"})
                    
                ], color="warning", style={
                    "background": "linear-gradient(135deg, rgba(255,215,0,0.15) 0%, rgba(255,215,0,0.08) 100%)", 
                    "border": "3px solid #ffd700", "border-radius": "1rem", "padding": "1.5rem"
                }),
                html.Hr(className="my-2", style={"border-color": "#495057"}),
                html.Label("Opacidad de las cajas:", className="mb-2", 
                         style={"color": "#00d4aa", "font-weight": "bold"}),
                dcc.Slider(
                    id="opacity-slider", min=0.1, max=1.0, value=0.3, step=0.1,
                    marks={i/10: str(i/10) for i in range(1, 11)}, className="mb-3"
                ),
                dbc.Checklist(
                    options=[
                        {"label": " Mostrar IDs", "value": "show_ids"},
                        {"label": " Mostrar coordenadas", "value": "show_coords"},
                    ],
                    value=["show_ids"], id="display-options", inline=True
                ),
                html.Hr(className="my-2"),
                html.Label("💡 Instrucciones:", className="mb-2", 
                         style={"color": "#00d4aa", "font-weight": "bold"}),
                dbc.Alert([
                    html.Strong("✏️ CREAR: ", style={"color": "#00d4aa"}), 
                    "Arrastra el mouse para dibujar", html.Br(),
                    html.Strong("🎯 SELECCIONAR: ", style={"color": "#00d4aa"}), 
                    "Clic en cualquier parte de la caja", html.Br(),
                    html.Strong("🎨 EDITAR: ", style={"color": "#00d4aa"}), 
                    "Arrastra bordes/esquinas", html.Br(), 
                    html.Strong("🗑️ ELIMINAR: ", style={"color": "#00d4aa"}), 
                    "Supr=Seleccionada • Botones=Última/ID", html.Br(),
                    html.Strong("⌨️ NAVEGAR: ", style={"color": "#00d4aa"}), 
                    "F=Siguiente • D=Anterior • Ctrl+Z=Deshacer", html.Br(),
                    html.Strong("💾 GUARDADO: ", style={"color": "#00d4aa"}), 
                    "Automático al editar"
                ], color="dark", className="small", 
                   style={"background": "rgba(0,212,170,0.1)", "border": "1px solid #00d4aa"})
            ], style={"background": "#1a1a1a"})
        ], className="mb-3", style={"background": "#1a1a1a", "border": "1px solid #495057", 
                                   "border-radius": "1rem"})
    
    def _create_statistics_panel(self):
        """Crear el panel de estadísticas"""
        return dbc.Card([
            dbc.CardHeader("📈 Estadísticas", 
                         style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                               "color": "#00d4aa", "font-weight": "bold", 
                               "border-bottom": "1px solid #495057"}),
            dbc.CardBody([
                html.Div(id="stats-content")
            ], style={"background": "#1a1a1a"})
        ], style={"background": "#1a1a1a", "border": "1px solid #495057", 
                 "border-radius": "1rem"})
    
    def _create_modals(self):
        """Crear los modals"""
        return dbc.Modal([
            dbc.ModalHeader("⚠️ Confirmar Eliminación"),
            dbc.ModalBody("¿Estás seguro de que quieres eliminar este frame? Esta acción no se puede deshacer."),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="cancel-delete", color="secondary"),
                dbc.Button("Eliminar", id="confirm-delete", color="danger")
            ])
        ], id="delete-modal", is_open=False)
    
    def _create_toast(self):
        """Crear el toast de notificaciones"""
        return dbc.Toast(
            id="notification-toast", header="Notificación", is_open=False,
            dismissable=True, duration=3000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350}
        )
    
    def setup_callbacks(self):
        """Configurar callbacks de Dash"""
        # JavaScript para capturar eventos de teclado
        self._setup_keyboard_callbacks()
        
        # Callbacks principales
        self._setup_navigation_callbacks()
        self._setup_annotation_callbacks()
        self._setup_interaction_callbacks()
        self._setup_utility_callbacks()
    
    def _setup_keyboard_callbacks(self):
        """Configurar callbacks de teclado"""
        clientside_callback(
            """
            function(n) {
                if (window.keydownListener) {
                    document.removeEventListener('keydown', window.keydownListener);
                }
                
                window.keydownListener = function(event) {
                    if (event.target.tagName !== 'INPUT' && event.target.tagName !== 'TEXTAREA') {
                        if (event.key === 'f' || event.key === 'F') {
                            const nextBtn = document.getElementById('next-button');
                            if (nextBtn) { nextBtn.click(); event.preventDefault(); }
                        } else if (event.key === 'd' || event.key === 'D') {
                            const prevBtn = document.getElementById('prev-button');
                            if (prevBtn) { prevBtn.click(); event.preventDefault(); }
                        } else if (event.ctrlKey && (event.key === 'z' || event.key === 'Z')) {
                            const undoBtn = document.getElementById('undo-button');
                            if (undoBtn) { undoBtn.click(); event.preventDefault(); }
                        } else if (event.key === 'Delete' || event.key === 'Supr') {
                            const deleteBtn = document.getElementById('delete-selected-button');
                            if (deleteBtn) { deleteBtn.click(); event.preventDefault(); }
                        }
                    }
                };
                
                document.addEventListener('keydown', window.keydownListener);
                return n + 1;
            }
            """,
            Output('keyboard-trigger', 'data'),
            [Input('keyboard-listener', 'id')]
        )
    
    def _setup_navigation_callbacks(self):
        """Configurar callbacks de navegación"""
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
            return self._handle_navigation_and_display(
                next_clicks, prev_clicks, first_clicks, last_clicks, reload_clicks,
                opacity, display_options, current_annotations
            )
    
    def _setup_annotation_callbacks(self):
        """Configurar callbacks de anotaciones"""
        @self.app.callback(
            Output('annotations-list', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_annotations_list(annotations):
            return self._update_annotations_list(annotations)
    
    def _setup_interaction_callbacks(self):
        """Configurar callbacks de interacción"""
        # Callback mejorado para detectar tanto edición como selección de bounding boxes
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open'),
             Output('notification-toast', 'children'),
             Output('selected-annotation', 'data', allow_duplicate=True)],
            [Input('image-graph', 'relayoutData')],
            [State('current-annotations', 'data'),
             State('image-dimensions', 'data'),
             State('current-image-data', 'data'),
             State('class-selector', 'value'),
             State('opacity-slider', 'value'),
             State('display-options', 'value'),
             State('selected-annotation', 'data')],
            prevent_initial_call=True
        )
        def handle_shape_interaction(relayout_data, annotations, img_dims, image_data, 
                                   selected_class, opacity, display_options, current_selected):
            if not relayout_data or not annotations:
                return dash.no_update, dash.no_update, False, "", dash.no_update
            
            print(f"DEBUG RELAYOUT: {relayout_data}")
            
            # PRIMERO: Manejar la edición normal (si hay cambios de coordenadas)
            edit_result = self.callback_manager.handle_shape_interaction(
                relayout_data, annotations, img_dims, image_data, 
                selected_class, opacity, display_options
            )
            
            # Si hay cambios de edición, usar esos datos actualizados
            if edit_result[0] != annotations:  # Si las anotaciones cambiaron
                updated_annotations = edit_result[0]
                updated_figure = edit_result[1]
                toast_open = edit_result[2]
                toast_message = edit_result[3]
                print("DEBUG: Cambios de edición detectados y aplicados")
            else:
                # No hay cambios de edición, usar datos originales
                updated_annotations = annotations
                updated_figure = None
                toast_open = False
                toast_message = ""
            
            # SEGUNDO: Detectar selección de shapes
            selected_annotation_idx = current_selected  # Mantener selección actual por defecto
            selection_message = toast_message
            
            # Buscar si hay información de shapes en relayout_data para selección
            for key, value in relayout_data.items():
                if 'shapes[' in key and '].x0' in key:
                    # Extraer el índice de la shape seleccionada
                    match = re.search(r'shapes\[(\d+)\]', key)
                    if match:
                        shape_idx = int(match.group(1))
                        if 0 <= shape_idx < len(updated_annotations):
                            selected_annotation_idx = shape_idx
                            class_name = updated_annotations[shape_idx].get('class_name', f"Clase {updated_annotations[shape_idx].get('class_id', 0)}")
                            selection_message = f"🎯 Seleccionada: {class_name} (índice: {shape_idx})"
                            print(f"DEBUG: Shape {shape_idx} seleccionada")
                            break
            
            # Si hay selección nueva O cambios de edición, regenerar figura
            if selected_annotation_idx != current_selected or updated_figure is None:
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                
                current_image = image_data.get('filename', self.image_files[self.current_image_index])
                final_figure, _ = self.figure_generator.create_figure_with_annotations(
                    current_image, updated_annotations, opacity, show_ids, show_coords, selected_annotation_idx
                )
                
                return updated_annotations, final_figure, toast_open or (selected_annotation_idx != current_selected), selection_message, selected_annotation_idx
            
            # Si no hay cambios, retornar lo que ya tenemos de la edición
            return updated_annotations, updated_figure or dash.no_update, toast_open, selection_message, selected_annotation_idx
        
        # Callback alternativo para detectar clics directos (cuando no hay edición)
        @self.app.callback(
            [Output('selected-annotation', 'data', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input('image-graph', 'clickData')],
            [State('current-annotations', 'data'),
             State('image-dimensions', 'data')],
            prevent_initial_call=True
        )
        def handle_direct_click(click_data, annotations, img_dims):
            if not click_data or not annotations or not img_dims:
                return dash.no_update, dash.no_update, dash.no_update
            
            try:
                # Obtener coordenadas del clic
                click_x = click_data['points'][0]['x']
                click_y = click_data['points'][0]['y']
                
                print(f"DEBUG DIRECT CLICK: Clic en ({click_x:.1f}, {click_y:.1f})")
                
                # Buscar qué anotación contiene este punto
                for i in reversed(range(len(annotations))):
                    ann = annotations[i]
                    
                    # Convertir anotación YOLO a píxeles
                    x_center = ann['x_center'] * img_dims['width']
                    y_center = ann['y_center'] * img_dims['height']
                    width = ann['width'] * img_dims['width']
                    height = ann['height'] * img_dims['height']
                    
                    # Calcular límites de la caja con margen
                    margin = 10
                    x_min = x_center - width / 2 - margin
                    x_max = x_center + width / 2 + margin
                    y_min = img_dims['height'] - (y_center + height / 2) - margin
                    y_max = img_dims['height'] - (y_center - height / 2) + margin
                    
                    if x_min <= click_x <= x_max and y_min <= click_y <= y_max:
                        class_name = ann.get('class_name', f"Clase {ann.get('class_id', 0)}")
                        message = f"🎯 Seleccionada por clic: {class_name} (índice: {i})"
                        print(f"DEBUG: Selección por clic directo - índice {i}")
                        return i, True, message
                
                return dash.no_update, False, ""
                
            except Exception as e:
                print(f"ERROR en clic directo: {e}")
                return dash.no_update, False, ""
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True),
             Output('selected-annotation', 'data', allow_duplicate=True)],
            [Input('delete-selected-button', 'n_clicks')],
            [State('current-annotations', 'data'),
             State('selected-annotation', 'data'),
             State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def delete_selected_annotation(delete_clicks, annotations, selected_id, image_data, opacity, display_options):
            return self.callback_manager.handle_delete_selected_annotation(
                delete_clicks, annotations, selected_id, image_data, opacity, display_options
            )
        
        # Callback para botones de selección en la lista de anotaciones
        @self.app.callback(
            [Output('selected-annotation', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input({"type": "select-btn", "index": ALL}, "n_clicks")],
            [State('current-annotations', 'data'),
             State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def handle_annotation_selection(select_clicks, annotations, image_data, opacity, display_options):
            if not any(select_clicks) or not annotations:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            # Encontrar qué botón fue presionado
            triggered_id = ctx.triggered[0]['prop_id']
            import json
            button_info = json.loads(triggered_id.split('.')[0])
            selected_idx = button_info['index']
            
            if 0 <= selected_idx < len(annotations):
                # Regenerar figura con selección resaltada
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                current_image = image_data.get('filename', self.image_files[self.current_image_index])
                
                updated_figure, _ = self.figure_generator.create_figure_with_annotations(
                    current_image, annotations, opacity, show_ids, show_coords, selected_idx
                )
                
                class_name = annotations[selected_idx].get('class_name', f"Clase {annotations[selected_idx].get('class_id', 0)}")
                message = f"🎯 Seleccionada desde lista: {class_name} (índice: {selected_idx})"
                
                print(f"DEBUG: Selección desde lista - índice {selected_idx}")
                
                return selected_idx, updated_figure, True, message
            
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Callback para manejar información de anotación seleccionada
        @self.app.callback(
            [
                Output('selected-info', 'children'),
                Output('selected-class-selector', 'disabled'),
                Output('change-class-button', 'disabled'),
                Output('selected-class-selector', 'value'),
                Output('change-class-button', 'style')
            ],
            [
                Input('selected-annotation', 'data'),
                Input('current-annotations', 'data')
            ]
        )
        def update_selected_info(selected_id, annotations):
            button_style_disabled = {"font-weight": "bold", "width": "100%", "opacity": "0.6"}
            button_style_enabled = {"font-weight": "bold", "width": "100%", "opacity": "1.0"}
            
            if selected_id is None or not annotations:
                return "🔍 Haz clic en cualquier bounding box para seleccionar una anotación y cambiar su clase", \
                       True, True, 0, button_style_disabled
            
            # Buscar la anotación seleccionada
            selected_ann = None
            if 0 <= selected_id < len(annotations):
                selected_ann = annotations[selected_id]
            
            if selected_ann is None:
                return "Anotación no encontrada", True, True, 0, button_style_disabled
            
            # Usar class_id o class dependiendo de lo que esté disponible
            class_idx = selected_ann.get('class_id', selected_ann.get('class', 0))
            if class_idx < len(self.classes):
                class_name = self.classes[class_idx]
            else:
                class_name = f"Clase {class_idx}"
                
            info_text = f"🎯 ANOTACIÓN SELECCIONADA → Índice: {selected_id} | Clase actual: {class_name} | ✅ Listo para cambiar"
            
            return info_text, False, False, class_idx, button_style_enabled

        # Callback para cambiar la clase de la anotación seleccionada
        @self.app.callback(
            [
                Output('current-annotations', 'data', allow_duplicate=True),
                Output('image-graph', 'figure', allow_duplicate=True),
                Output('selected-annotation', 'data', allow_duplicate=True),
                Output('notification-toast', 'is_open', allow_duplicate=True),
                Output('notification-toast', 'children', allow_duplicate=True)
            ],
            Input('change-class-button', 'n_clicks'),
            [
                State('selected-annotation', 'data'),
                State('selected-class-selector', 'value'),
                State('current-annotations', 'data'),
                State('image-graph', 'figure'),
                State('image-dimensions', 'data'),
                State('opacity-slider', 'value'),
                State('display-options', 'value')
            ],
            prevent_initial_call=True
        )
        def change_selected_class(n_clicks, selected_id, new_class, annotations, figure, dims, opacity, display_options):
            print(f"DEBUG CLASS CHANGE START: n_clicks={n_clicks}, selected_id={selected_id}, new_class={new_class} (type: {type(new_class)})")
            
            if not n_clicks or selected_id is None or not annotations:
                print("DEBUG CLASS CHANGE: Condiciones no cumplidas")
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            try:
                # Cambiar la clase de la anotación seleccionada
                updated_annotations = annotations.copy()
                if 0 <= selected_id < len(updated_annotations):
                    # Obtener el nombre de la imagen actual
                    current_image = self.image_files[self.current_image_index]
                    
                    # Guardar estado actual antes del cambio
                    self.callback_manager.undo_manager.push_state(
                        current_image, 
                        annotations
                    )
                    
                    # Obtener el nombre de la clase anterior para el mensaje
                    old_class_name = updated_annotations[selected_id]['class_name']
                    
                    # Convertir new_class a entero si es string
                    if isinstance(new_class, str):
                        new_class = int(new_class)
                    
                    # Validar que el índice de clase sea válido
                    if not (0 <= new_class < len(self.classes)):
                        print(f"ERROR: Índice de clase inválido: {new_class}")
                        error_message = f"❌ Error: Índice de clase inválido ({new_class})"
                        return dash.no_update, dash.no_update, dash.no_update, True, error_message
                    
                    # Actualizar la clase (usar tanto class como class_id para compatibilidad)
                    updated_annotations[selected_id]['class'] = new_class
                    updated_annotations[selected_id]['class_id'] = new_class
                    updated_annotations[selected_id]['class_name'] = self.classes[new_class]
                    
                    # Guardar cambios automáticamente
                    try:
                        self.annotation_manager.save_annotations(
                            current_image, 
                            updated_annotations
                        )
                    except Exception as save_error:
                        print(f"ERROR guardando cambio de clase: {save_error}")
                    
                    # Regenerar la figura
                    show_ids = 'show_ids' in (display_options or ['show_ids'])
                    show_coords = 'show_coords' in (display_options or [])
                    updated_figure, _ = self.figure_generator.create_figure_with_annotations(
                        current_image,
                        updated_annotations, opacity, show_ids, show_coords, selected_id
                    )
                    
                    print(f"DEBUG CLASS CHANGE SUCCESS: Índice={selected_id}, Old Class={old_class_name}, New Class={self.classes[new_class]}")
                    
                    # Mensaje de éxito
                    success_message = f"✅ Cambiado exitosamente: {old_class_name} → {self.classes[new_class]} (índice: {selected_id})"
                    
                    return updated_annotations, updated_figure, selected_id, True, success_message
                
            except Exception as e:
                print(f"ERROR changing class: {e}")
                import traceback
                traceback.print_exc()
                error_message = f"❌ Error cambiando clase: {str(e)}"
                return dash.no_update, dash.no_update, dash.no_update, True, error_message
            
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

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
            return self.callback_manager.handle_delete_annotation(
                delete_clicks, annotations, image_data, opacity, display_options
            )
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input('undo-button', 'n_clicks')],
            [State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def undo_action(undo_clicks, image_data, opacity, display_options):
            return self.callback_manager.handle_undo_action(
                undo_clicks, image_data, opacity, display_options
            )
        
        # Callbacks para eliminación simplificada
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input('delete-last-button', 'n_clicks')],
            [State('current-annotations', 'data'),
             State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def delete_last_annotation(delete_clicks, annotations, image_data, opacity, display_options):
            return self.callback_manager.handle_delete_last_annotation(
                delete_clicks, annotations, image_data, opacity, display_options
            )
        
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True),
             Output('delete-id-input', 'value')],
            [Input('delete-by-id-button', 'n_clicks')],
            [State('current-annotations', 'data'),
             State('delete-id-input', 'value'),
             State('current-image-data', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def delete_by_id_annotation(delete_clicks, annotations, delete_id, image_data, opacity, display_options):
            return self.callback_manager.handle_delete_by_id_annotation(
                delete_clicks, annotations, delete_id, image_data, opacity, display_options
            )
    
    def _setup_utility_callbacks(self):
        """Configurar callbacks de utilidades"""
        @self.app.callback(
            Output('stats-content', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_statistics(annotations):
            return self._update_statistics(annotations)
    
    # Métodos de implementación de callbacks
    def _handle_navigation_and_display(self, next_clicks, prev_clicks, first_clicks, last_clicks, 
                                     reload_clicks, opacity, display_options, current_annotations):
        """Implementar navegación y actualización de display"""
        image_changed = False
        
        if ctx.triggered:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'next-button' and next_clicks:
                new_index = min(self.current_image_index + 1, len(self.image_files) - 1)
                image_changed = new_index != self.current_image_index
                self.current_image_index = new_index
            elif button_id == 'prev-button' and prev_clicks:
                new_index = max(self.current_image_index - 1, 0)
                image_changed = new_index != self.current_image_index
                self.current_image_index = new_index
            elif button_id == 'first-button' and first_clicks:
                image_changed = self.current_image_index != 0
                self.current_image_index = 0
            elif button_id == 'last-button' and last_clicks:
                new_index = len(self.image_files) - 1
                image_changed = self.current_image_index != new_index
                self.current_image_index = new_index
            elif button_id == 'reload-button':
                image_changed = True  # Forzar recarga
            elif button_id in ['opacity-slider', 'display-options']:
                # Solo actualizar display - NO cambiar imagen
                current_image = self.image_files[self.current_image_index]
                show_ids = 'show_ids' in (display_options or [])
                show_coords = 'show_coords' in (display_options or [])
                
                fig, img_dims = self.figure_generator.create_figure_with_annotations(
                    current_image, current_annotations or [], opacity, show_ids, show_coords
                )
                
                counter_text = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
                badge_text = f"{len(current_annotations or [])} anotaciones"
                
                return fig, current_annotations, counter_text, img_dims, {'filename': current_image}, badge_text
        else:
            # Primera carga
            image_changed = True
        
        current_image = self.image_files[self.current_image_index]
        
        # Solo cargar desde archivo si la imagen cambió
        if image_changed:
            print(f"DEBUG: Cambiando a imagen: {current_image}")
            annotations = self.annotation_manager.load_annotations(current_image)
        else:
            # Mantener anotaciones actuales si solo cambió la visualización
            annotations = current_annotations or []
        
        show_ids = 'show_ids' in (display_options or ['show_ids'])
        show_coords = 'show_coords' in (display_options or [])
        
        fig, img_dims = self.figure_generator.create_figure_with_annotations(
            current_image, annotations, opacity, show_ids, show_coords
        )
        
        counter_text = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
        badge_text = f"{len(annotations)} anotaciones"
        
        return fig, annotations, counter_text, img_dims, {'filename': current_image}, badge_text
    
    def _update_annotations_list(self, annotations):
        """Actualizar lista de anotaciones"""
        if not annotations:
            return [dbc.Alert([
                "📭 No hay anotaciones en esta imagen", html.Br(),
                html.Small("💡 Dibuja un rectángulo para crear una nueva", className="text-muted")
            ], color="info", className="text-center")]
        
        items = []
        for idx, ann in enumerate(annotations):
            items.append(
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6(f"🏷️ {ann['class_name']}", className="card-title mb-1", 
                                       style={"color": "#00d4aa", "font-weight": "bold"}),
                                html.Small(f"Índice: {idx}", className="text-muted"),
                            ], width=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("🎯", id={"type": "select-btn", "index": idx}, 
                                             size="sm", color="warning", title="Seleccionar para cambiar clase", 
                                             className="shadow-sm"),
                                    dbc.Button("🗑️", id={"type": "delete-btn", "index": ann.get('id', idx)}, 
                                             size="sm", color="danger", title="Eliminar", 
                                             className="shadow-sm")
                                ], size="sm")
                            ], width=6, className="text-end")
                        ]),
                        html.Hr(className="my-2", style={"border-color": "#495057"}),
                        html.Small([
                            f"Centro: ({ann['x_center']:.3f}, {ann['y_center']:.3f})", html.Br(),
                            f"Tamaño: {ann['width']:.3f} × {ann['height']:.3f}", html.Br(),
                            html.Strong("🎯 Seleccionar para cambiar clase • 💡 Arrastra bordes para redimensionar", 
                                      className="text-info", style={"color": "#00d4aa !important"})
                        ], className="text-muted")
                    ], className="py-2", style={"background": "#2d3748"})
                ], className="mb-2", 
                   style={"border-left": f"4px solid {self.class_colors[ann['class_id'] % len(self.class_colors)]}", 
                          "box-shadow": "0 4px 8px rgba(0,212,170,0.1)", "background": "#2d3748", 
                          "border": "1px solid #495057", "border-radius": "0.5rem"})
            )
        
        return items
    
    def _update_statistics(self, annotations):
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
            html.P([html.Strong("📊 Total: ", style={"color": "#00d4aa"}), 
                   f"{len(annotations)} anotaciones"], style={"color": "#adb5bd"}),
            html.P([html.Strong("📏 Área promedio: ", style={"color": "#00d4aa"}), 
                   f"{avg_area:.4f}"], style={"color": "#adb5bd"}),
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
    
    def run(self, debug=True, port=8050, host='127.0.0.1'):
        """Ejecutar la aplicación"""
        print("🚀 Iniciando Herramienta Avanzada de Corrección de Etiquetado...")
        print(f"📁 Dataset: {self.dataset_path}")
        print(f"📄 Archivo YAML de clases: {self.config_loader.config_path}")
        print(f"🖼️ Imágenes encontradas: {len(self.image_files)}")
        print(f"🏷️ Clases disponibles ({len(self.classes)}): {', '.join(self.classes)}")
        print(f"🎨 Colores personalizados: {'✅ Sí' if len(self.class_colors) == len(self.classes) else '❌ Por defecto'}")
        print(f"🌐 Servidor iniciando en: http://{host}:{port}")
        print("\n" + "="*60)
        print("💡 FUNCIONALIDADES IMPLEMENTADAS:")
        print("• ⌨️ NAVEGACIÓN: F=Siguiente, D=Anterior, Ctrl+Z=Deshacer")
        print("• ✏️ EDICIÓN: Dibuja para crear, arrastra bordes para redimensionar")  
        print("• 🎯 SELECCIÓN: Clic en cualquier parte de la caja para seleccionar")
        print("• 🗑️ ELIMINACIÓN: Supr=Seleccionada, Botones=Última/ID específico")
        print("• 💾 GUARDADO: Automático al crear, editar o eliminar")
        print("• 🎨 PERSONALIZACIÓN: Clases y colores desde YAML")
        print("• 📊 ESTADÍSTICAS: Conteo por clase y área promedio")
        print("="*60)
        
        self.app.run(debug=debug, port=port, host=host)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Herramienta Avanzada de Corrección de Etiquetado")
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset_cruce_3",
        help="Ruta del dataset a usar (ej: dataset_cruce_3)"
    )
    args = parser.parse_args()

    try:
        tool = AdvancedAnnotationTool(dataset_path=args.dataset)
        tool.run(debug=False, port=8050)
    except Exception as e:
        print(f"❌ Error iniciando la aplicación: {e}")
        print("💡 Asegúrate de que:")
        print(f"  - El directorio {args.dataset} existe")
        print("  - Hay imágenes en train/images/")
        print("  - El archivo classes.yaml existe con las clases definidas")
        print("  - Las dependencias están instaladas")
