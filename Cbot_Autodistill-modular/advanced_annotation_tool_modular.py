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
        
        # Configurar la app Dash con tema moderno
        external_stylesheets = [
            dbc.themes.BOOTSTRAP,
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
            {
                "href": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
                "rel": "stylesheet"
            }
        ]
        

        self.app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
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
        self.app.layout = html.Div([
            dbc.Container([
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
                
            ], fluid=True)
        ])
    
    def _create_header(self):
        """Crear el header de la aplicación con diseño moderno"""
        return html.Div([
            dbc.Navbar([
                dbc.Container([
                    # Brand/Logo
                    dbc.NavbarBrand([
                        html.I(className="fas fa-vector-square me-2", 
                              style={"color": "#2563eb", "font-size": "1.5rem"}),
                        "Advanced Annotation Tool"
                    ], style={
                        "font-family": "Inter, sans-serif", 
                        "font-weight": "600",
                        "font-size": "1.3rem",
                        "color": "#1f2937"
                    }),
                    
                    # Status info
                    dbc.Nav([
                        dbc.NavItem([
                            html.Div([
                                html.I(className="fas fa-database me-1", style={"color": "#6b7280"}),
                                html.Span("YOLO Dataset Editor", className="small text-muted")
                            ])
                        ])
                    ], className="ms-auto")
                ], fluid=True)
            ], color="white", className="border-bottom shadow-sm mb-4", 
               style={"border-bottom": "1px solid #e5e7eb !important"})
        ])
    
    def _create_control_panel(self):
        """Crear el panel de control"""
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # Navegación
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-folder-open me-2", style={"color": "#6366f1"}),
                                "Navegación"
                            ], className="mb-3 text-body fw-semibold", style={"font-size": "0.9rem"}),
                            dbc.ButtonGroup([
                                dbc.Button([
                                    html.I(className="fas fa-angle-double-left me-1"),
                                    "Primero"
                                ], id="first-button", color="light", outline=True,
                                 size="sm", className="border-secondary"),
                                dbc.Button([
                                    html.I(className="fas fa-chevron-left me-1"),
                                    "Anterior"
                                ], id="prev-button", color="primary", 
                                 size="sm"),
                                dbc.Button([
                                    "Siguiente",
                                    html.I(className="fas fa-chevron-right ms-1")
                                ], id="next-button", color="primary", 
                                 size="sm"),
                                dbc.Button([
                                    "Último",
                                    html.I(className="fas fa-angle-double-right ms-1")
                                ], id="last-button", color="light", outline=True,
                                 size="sm", className="border-secondary"),
                            ], className="w-100"),
                        ])
                    ], width=3),
                    
                    # Estado
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-chart-bar me-2", style={"color": "#10b981"}),
                                "Estado"
                            ], className="mb-3 text-body fw-semibold", style={"font-size": "0.9rem"}),
                            dbc.Card([
                                dbc.CardBody([
                                    html.P(id="image-counter", className="text-center mb-0 fw-bold",
                                          style={"font-size": "0.85rem", "color": "#374151"})
                                ], className="py-2")
                            ], className="bg-light border-0 shadow-sm")
                        ])
                    ], width=3),
                    
                    # Herramientas
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-tools me-2", style={"color": "#f59e0b"}),
                                "Herramientas"
                            ], className="mb-3 text-body fw-semibold", style={"font-size": "0.9rem"}),
                            
                            # Botón principal de deshacer
                            dbc.Button([
                                html.I(className="fas fa-undo me-2"),
                                "Deshacer"
                            ], id="undo-button", color="warning", outline=True,
                             size="sm", className="mb-3 w-100", title="Ctrl+Z"),
                            
                            # Menú desplegable de eliminación
                            dbc.ButtonGroup([
                                dbc.Button([
                                    html.I(className="fas fa-trash me-1"),
                                    "Eliminar"
                                ], color="danger", outline=True, size="sm", disabled=True),
                                dbc.DropdownMenu([
                                    dbc.DropdownMenuItem([
                                        html.I(className="fas fa-mouse-pointer me-2"),
                                        "Seleccionada"
                                    ], id="delete-selected-button", className="py-2"),
                                    dbc.DropdownMenuItem(divider=True),
                                    dbc.DropdownMenuItem([
                                        html.I(className="fas fa-arrow-left me-2"),
                                        "Última anotación"
                                    ], id="delete-last-button", className="py-2"),
                                    dbc.DropdownMenuItem([
                                        html.I(className="fas fa-image me-2"),
                                        "Todo el frame"
                                    ], id="delete-frame-button", className="py-2"),
                                    dbc.DropdownMenuItem(divider=True),
                                    dbc.DropdownMenuItem([
                                        html.Div([
                                            html.I(className="fas fa-hashtag me-2"),
                                            "Por ID:",
                                            dbc.InputGroup([
                                                dbc.Input(
                                                    id="delete-id-input", 
                                                    type="number", 
                                                    placeholder="ID", 
                                                    size="sm",
                                                    min=0,
                                                    className="mt-1",
                                                    style={"width": "70px"}
                                                ),
                                                dbc.Button([
                                                    html.I(className="fas fa-trash")
                                                ], id="delete-by-id-button", 
                                                 color="danger", outline=True, size="sm",
                                                 className="mt-1")
                                            ], size="sm")
                                        ])
                                    ], header=True, className="px-3")
                                ], 
                                toggle_style={"border": "none"},
                                direction="up",
                                size="sm")
                            ], className="w-100 mb-2"),
                            
                            html.Small([
                                html.I(className="fas fa-lightbulb me-1"),
                                "Arrastra para crear • Clic para seleccionar"
                            ], className="text-muted d-block", style={"font-size": "0.75rem"})
                        ])
                    ], width=3),
                    
                    # Acciones y Configuración
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-cogs me-2", style={"color": "#8b5cf6"}),
                                "Configuración"
                            ], className="mb-3 text-body fw-semibold", style={"font-size": "0.9rem"}),
                            
                            # Botón de recarga
                            dbc.Button([
                                html.I(className="fas fa-sync-alt me-2"),
                                "Recargar Dataset"
                            ], id="reload-button", color="info", outline=True,
                             size="sm", className="w-100 mb-3"),
                             
                            # Información de atajos compacta
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6([
                                        html.I(className="fas fa-keyboard me-2", style={"color": "#6b7280"}),
                                        "Atajos"
                                    ], className="mb-2", style={"font-size": "0.8rem"}),
                                    html.Div([
                                        dbc.Badge("F", color="light", text_color="dark", className="me-1"),
                                        html.Small("Siguiente", className="me-3 text-muted"),
                                        dbc.Badge("D", color="light", text_color="dark", className="me-1"),
                                        html.Small("Anterior", className="text-muted"),
                                    ], className="mb-1"),
                                    html.Div([
                                        dbc.Badge("Ctrl+Z", color="light", text_color="dark", className="me-1"),
                                        html.Small("Deshacer", className="me-2 text-muted"),
                                        dbc.Badge("Supr", color="light", text_color="dark", className="me-1"),
                                        html.Small("Eliminar", className="text-muted"),
                                    ])
                                ], className="py-2")
                            ], className="border-0 bg-light", style={"border-radius": "8px"})
                        ])
                    ], width=3)
                ])
            ], className="p-4")
        ], className="mb-4 border-0 shadow-sm", style={"border-radius": "12px"})
    
    def _create_main_content(self):
        """Crear el contenido principal"""
        return dbc.Row([
            # Visor de imágenes
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.H5([
                                html.I(className="fas fa-image me-2", style={"color": "#3b82f6"}),
                                "Visor de Imágenes"
                            ], className="mb-0 text-body fw-semibold"),
                            dbc.Badge(id="annotation-count-badge", color="primary", pill=True, className="ms-auto")
                        ], className="d-flex align-items-center justify-content-between")
                    ], className="bg-white border-bottom border-light"),
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
                            style={'height': '70vh', 'width': '100%'}
                        ),
                        html.Div([
                            html.I(className="fas fa-mouse-pointer me-1", style={"color": "#6b7280"}),
                            html.Span(id="mouse-coords", className="text-muted small")
                        ], className="mt-2 px-2")
                    ], className="p-3 bg-light")
                ], className="border-0 shadow-sm", style={"border-radius": "12px"})
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
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-tags me-2", style={"color": "#f59e0b"}),
                    "Lista de Anotaciones"
                ], className="mb-0 text-body fw-semibold")
            ], className="bg-white border-bottom border-light"),
            dbc.CardBody([
                html.Div(id="annotations-list", 
                        style={'max-height': '320px', 'overflow-y': 'auto'},
                        className="custom-scrollbar")
            ], className="p-3")
        ], className="mb-4 border-0 shadow-sm", style={"border-radius": "12px"})
    
    def _create_configuration_panel(self):
        """Crear el panel de configuración"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-cog me-2", style={"color": "#8b5cf6"}),
                    "Configuración"
                ], className="mb-0 text-body fw-semibold")
            ], className="bg-white border-bottom border-light"),
            dbc.CardBody([
                # Nueva clase para anotaciones
                html.Div([
                    html.Label([
                        html.I(className="fas fa-plus-circle me-2", style={"color": "#10b981"}),
                        "Clase para nuevas anotaciones"
                    ], className="mb-2 fw-semibold text-body", style={"font-size": "0.9rem"}),
                    dbc.Select(
                        id="class-selector",
                        options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                        value=0, size="sm", className="mb-4"
                    )
                ]),
                
                # Sección para cambiar clase - más limpia
                dbc.Card([
                    dbc.CardHeader([
                        html.H6([
                            html.I(className="fas fa-edit me-2", style={"color": "#f59e0b"}),
                            "Cambiar Clase Seleccionada"
                        ], className="mb-0 text-body fw-semibold")
                    ], className="bg-light border-0"),
                    dbc.CardBody([
                        dbc.Alert(id="selected-info", color="info", className="mb-3 text-center small"),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Label("Nueva clase:", className="mb-2 small fw-semibold"),
                                dbc.Select(
                                    id="selected-class-selector",
                                    options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                                    value=0, size="sm", disabled=True
                                )
                            ], width=7),
                            dbc.Col([
                                html.Label("Aplicar:", className="mb-2 small fw-semibold"),
                                dbc.Button([
                                    html.I(className="fas fa-check me-1"),
                                    "Cambiar"
                                ], id="change-class-button", color="warning", 
                                 size="sm", disabled=True, className="w-100")
                            ], width=5)
                        ]),
                        
                        html.Small([
                            html.I(className="fas fa-lightbulb me-1"),
                            "Haz clic en una caja o usa el botón 🎯 para seleccionar"
                        ], className="text-muted d-block mt-2")
                    ], className="py-3")
                ], className="mb-4 border-0 bg-light"),
                
                # Controles de visualización
                html.Div([
                    html.Label([
                        html.I(className="fas fa-eye me-2", style={"color": "#6366f1"}),
                        "Visualización"
                    ], className="mb-3 fw-semibold text-body", style={"font-size": "0.9rem"}),
                    
                    html.Label("Opacidad:", className="mb-2 small fw-semibold"),
                    dcc.Slider(
                        id="opacity-slider", min=0.1, max=1.0, value=0.3, step=0.1,
                        marks={0.1: '0.1', 0.5: '0.5', 1.0: '1.0'}, className="mb-3"
                    ),
                    
                    dbc.Checklist(
                        options=[
                            {"label": "Mostrar IDs", "value": "show_ids"},
                            {"label": "Mostrar coordenadas", "value": "show_coords"},
                        ],
                        value=["show_ids"], id="display-options", inline=True,
                        className="mb-3"
                    )
                ]),
                
                # Instrucciones compactas
                dbc.Card([
                    dbc.CardBody([
                        html.H6([
                            html.I(className="fas fa-info-circle me-2", style={"color": "#3b82f6"}),
                            "Atajos de Teclado"
                        ], className="mb-2 text-body fw-semibold small"),
                        html.Div([
                            html.Small("F: Siguiente imagen", className="d-block text-muted"),
                            html.Small("D: Imagen anterior", className="d-block text-muted"),
                            html.Small("Ctrl+Z: Deshacer", className="d-block text-muted"),
                            html.Small("Supr: Eliminar seleccionada", className="d-block text-muted")
                        ])
                    ], className="py-2")
                ], className="border-0 bg-light")
            ], className="p-3")
        ], className="mb-4 border-0 shadow-sm", style={"border-radius": "12px"})
    
    def _create_statistics_panel(self):
        """Crear el panel de estadísticas"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-chart-bar me-2", style={"color": "#ef4444"}),
                    "Estadísticas"
                ], className="mb-0 text-body fw-semibold")
            ], className="bg-white border-bottom border-light"),
            dbc.CardBody([
                html.Div(id="stats-content")
            ], className="p-3")
        ], className="border-0 shadow-sm", style={"border-radius": "12px"})
    
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
                html.Div([
                    html.I(className="fas fa-inbox fa-2x mb-2", style={"color": "#94a3b8"}),
                    html.H6("No hay anotaciones", className="mb-1"),
                    html.Small("Dibuja un rectángulo para crear una nueva", className="text-muted")
                ], className="text-center")
            ], color="light", className="border-0 bg-light")]
        
        items = []
        for idx, ann in enumerate(annotations):
            # Color de borde más suave
            border_color = self.class_colors[ann['class_id'] % len(self.class_colors)]
            
            items.append(
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.I(className="fas fa-tag me-2", 
                                          style={"color": border_color, "font-size": "0.9rem"}),
                                    html.Span(ann['class_name'], className="fw-semibold text-dark")
                                ], className="d-flex align-items-center mb-1"),
                                html.Small(f"ID: {idx}", className="text-muted", style={"font-size": "0.75rem"}),
                            ], width=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-crosshairs")
                                    ], id={"type": "select-btn", "index": idx}, 
                                     size="sm", color="warning", outline=True, 
                                     title="Seleccionar para cambiar clase"),
                                    dbc.Button([
                                        html.I(className="fas fa-trash")
                                    ], id={"type": "delete-btn", "index": ann.get('id', idx)}, 
                                     size="sm", color="danger", outline=True, 
                                     title="Eliminar")
                                ], size="sm")
                            ], width=6, className="text-end")
                        ]),
                        html.Hr(className="my-2 border-light"),
                        html.Div([
                            html.Small([
                                html.I(className="fas fa-crosshairs me-1", style={"color": "#6b7280"}),
                                f"Centro: ({ann['x_center']:.3f}, {ann['y_center']:.3f})"
                            ], className="d-block text-muted mb-1", style={"font-size": "0.75rem"}),
                            html.Small([
                                html.I(className="fas fa-expand-arrows-alt me-1", style={"color": "#6b7280"}),
                                f"Tamaño: {ann['width']:.3f} × {ann['height']:.3f}"
                            ], className="d-block text-muted mb-2", style={"font-size": "0.75rem"}),
                            dbc.Alert([
                                html.I(className="fas fa-info-circle me-1"),
                                html.Small("Haz clic en 🎯 para seleccionar • Arrastra bordes para redimensionar")
                            ], color="info", className="py-1 mb-0 border-0", 
                               style={"background-color": "#e7f3ff", "font-size": "0.7rem"})
                        ])
                    ], className="p-3")
                ], className="mb-3 border-0 shadow-sm", 
                   style={
                       "border-left": f"4px solid {border_color} !important", 
                       "border-radius": "8px",
                       "background": "white"
                   })
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
