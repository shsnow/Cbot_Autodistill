import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, clientside_callback, no_update
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import sys
import argparse
import re
import json

# Importar las utilidades desde el directorio utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import (
    ConfigLoader, AnnotationManager, CoordinateConverter, 
    UndoManager, FigureGenerator, CallbackManager
)

# Configuración de la aplicación Dash
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://use.fontawesome.com/releases/v6.0.0/css/all.css",
        {
            "href": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
            "rel": "stylesheet"
        }
    ],
    assets_folder='assets',
    suppress_callback_exceptions=True
)

app.title = "AutoDistill Suite - Herramienta de Anotación Completa"

class AdvancedAnnotationSuite:
    def __init__(self, app):
        self.app = app
        
        # Configurar dataset por defecto
        self.dataset_path = "CRUCE_COLON_1_class"
        self.classes_yaml = "data.yaml"
        self.images_path = os.path.join(self.dataset_path)  # Las imágenes están directamente en el directorio
        self.labels_path = os.path.join(self.dataset_path, "labels")
        
        # Crear directorio de labels si no existe
        if not os.path.exists(self.labels_path):
            os.makedirs(self.labels_path)
        
        # Inicializar módulos
        self._initialize_modules()
        
        # Variables de estado
        self.current_image_index = 0
        self.selected_annotation_id = None
        
        # Cargar archivos de imagen
        self._load_image_files()
        
    def _initialize_modules(self):
        """Inicializar todos los módulos necesarios"""
        # Cargar configuración
        self.config_loader = ConfigLoader(self.classes_yaml)
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
    
    def _load_image_files(self):
        """Cargar lista de archivos de imagen"""
        self.image_files = sorted([
            f for f in os.listdir(self.images_path) 
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if not self.image_files:
            raise FileNotFoundError(f"No se encontraron imágenes en: {self.images_path}")
        
        print(f"✅ Se encontraron {len(self.image_files)} imágenes")
    
    def create_navbar(self):
        """Crear la barra de navegación"""
        return dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("🏠 Inicio", id="nav-home", href="#", active="exact")),
                dbc.NavItem(dbc.NavLink("🏷️ Anotación", id="nav-annotation", href="#", className="active")),
                dbc.NavItem(dbc.NavLink("🤖 AutoDistill", id="nav-autodistill", href="#")),
                dbc.NavItem(dbc.NavLink("📁 Archivos", id="nav-files", href="#")),
            ],
            brand="AutoDistill Suite - Herramienta de Anotación",
            brand_href="#",
            color="dark",
            dark=True,
            className="mb-4"
        )
    
    def create_annotation_page(self):
        """Crear la página completa de anotación con toda la funcionalidad original"""
        return dbc.Container([
            # Stores para mantener el estado
            dcc.Store(id='current-annotations', data=[]),
            dcc.Store(id='current-image-data', data={}),
            dcc.Store(id='image-dimensions', data={}),
            dcc.Store(id='selected-annotation', data=None),
            dcc.Store(id='keyboard-trigger', data=0),
            
            # Elemento invisible para el listener de teclado
            html.Div(id="keyboard-listener", style={"display": "none"}),
            
            # Header con información del dataset
            self._create_header(),
            
            # Panel de control principal
            self._create_control_panel(),
            
            # Contenido principal
            dbc.Row([
                # Visor de imágenes
                dbc.Col([
                    self._create_image_viewer()
                ], width=8),
                
                # Sidebar con controles
                dbc.Col([
                    self._create_annotations_list(),
                    self._create_configuration_panel(),
                    self._create_statistics_panel()
                ], width=4)
            ]),
            
            # Modals
            self._create_modals(),
            
            # Toast para notificaciones
            self._create_toast(),
            
        ], fluid=True)
    
    def _create_header(self):
        """Crear el header de la aplicación"""
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-vector-square me-2", 
                                          style={"color": "#00d4aa"}),
                                    "Herramienta Avanzada de Anotación"
                                ], className="mb-2 text-light"),
                                html.P([
                                    html.I(className="fas fa-folder-open me-2", style={"color": "#adb5bd"}),
                                    f"Dataset: {self.dataset_path} | Clases: {len(self.classes)} | Imágenes: {len(self.image_files)}"
                                ], className="mb-0 text-muted small")
                            ])
                        ], width=8),
                        dbc.Col([
                            dbc.Button("← Volver al Inicio", id="back-home", color="secondary", size="sm")
                        ], width=4, className="text-end")
                    ])
                ], className="py-3")
            ], className="mb-4 border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
        ])
    
    def _create_control_panel(self):
        """Crear el panel de control completo"""
        return dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # Navegación
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-navigation me-2", style={"color": "#00d4aa"}),
                                "Navegación"
                            ], className="mb-3 text-light fw-semibold"),
                            dbc.ButtonGroup([
                                dbc.Button([
                                    html.I(className="fas fa-angle-double-left me-1"),
                                    "Primero"
                                ], id="first-button", color="info", outline=True, size="sm"),
                                dbc.Button([
                                    html.I(className="fas fa-chevron-left me-1"),
                                    "Anterior (D)"
                                ], id="prev-button", color="primary", size="sm"),
                                dbc.Button([
                                    "Siguiente (F)",
                                    html.I(className="fas fa-chevron-right ms-1")
                                ], id="next-button", color="primary", size="sm"),
                                dbc.Button([
                                    "Último",
                                    html.I(className="fas fa-angle-double-right ms-1")
                                ], id="last-button", color="info", outline=True, size="sm"),
                            ], className="w-100"),
                        ])
                    ], width=3),
                    
                    # Estado de la imagen
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-image me-2", style={"color": "#00d4aa"}),
                                "Estado"
                            ], className="mb-3 text-light fw-semibold"),
                            dbc.Alert([
                                html.P(id="image-counter", className="text-center mb-0 fw-bold")
                            ], color="info", className="py-2 mb-0")
                        ])
                    ], width=3),
                    
                    # Herramientas
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-tools me-2", style={"color": "#00d4aa"}),
                                "Herramientas"
                            ], className="mb-3 text-light fw-semibold"),
                            
                            dbc.ButtonGroup([
                                dbc.Button([
                                    html.I(className="fas fa-undo me-1"),
                                    "Deshacer (Ctrl+Z)"
                                ], id="undo-button", color="warning", size="sm"),
                                dbc.Button([
                                    html.I(className="fas fa-sync-alt me-1"),
                                    "Recargar"
                                ], id="reload-button", color="info", size="sm"),
                            ], className="w-100 mb-2"),
                            
                            html.Small([
                                html.I(className="fas fa-lightbulb me-1"),
                                "Arrastra para crear • Clic para seleccionar"
                            ], className="text-muted d-block")
                        ])
                    ], width=3),
                    
                    # Eliminación
                    dbc.Col([
                        html.Div([
                            html.H6([
                                html.I(className="fas fa-trash me-2", style={"color": "#ff6b6b"}),
                                "Eliminación"
                            ], className="mb-3 text-light fw-semibold"),
                            
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-trash me-1"),
                                        "Seleccionada"
                                    ], id="delete-selected-button", color="danger", size="sm", 
                                     className="w-100 mb-1"),
                                    dbc.Button([
                                        html.I(className="fas fa-arrow-left me-1"),
                                        "Última"
                                    ], id="delete-last-button", color="danger", outline=True,
                                     size="sm", className="w-100")
                                ], width=6),
                                dbc.Col([
                                    dbc.InputGroup([
                                        dbc.Input(
                                            id="delete-id-input", 
                                            type="number", 
                                            placeholder="ID", 
                                            size="sm",
                                            min=0
                                        ),
                                        dbc.Button([
                                            html.I(className="fas fa-trash")
                                        ], id="delete-by-id-button", 
                                         color="danger", size="sm")
                                    ], size="sm", className="mb-1"),
                                    dbc.Button([
                                        "Frame completo"
                                    ], id="delete-frame-button", color="danger", 
                                     outline=True, size="sm", className="w-100")
                                ], width=6)
                            ])
                        ])
                    ], width=3)
                ]),
                
                # Información de atajos de teclado
                html.Hr(className="my-3", style={"border-color": "#495057"}),
                dbc.Alert([
                    html.Div([
                        html.Strong("⌨️ Atajos de Teclado: ", className="me-3"),
                        dbc.Badge("F", color="light", text_color="dark", className="me-1"),
                        html.Span("Siguiente", className="me-3 small"),
                        dbc.Badge("D", color="light", text_color="dark", className="me-1"),
                        html.Span("Anterior", className="me-3 small"),
                        dbc.Badge("Ctrl+Z", color="light", text_color="dark", className="me-1"),
                        html.Span("Deshacer", className="me-3 small"),
                        dbc.Badge("Supr", color="light", text_color="dark", className="me-1"),
                        html.Span("Eliminar seleccionada", className="small")
                    ], className="d-flex align-items-center justify-content-center flex-wrap")
                ], color="dark", className="mb-0 text-center")
            ], className="p-4")
        ], className="mb-4 border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
    
    def _create_image_viewer(self):
        """Crear el visor de imágenes"""
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.H5([
                        html.I(className="fas fa-image me-2", style={"color": "#00d4aa"}),
                        "Visor de Imágenes"
                    ], className="mb-0 text-light fw-semibold"),
                    dbc.Badge(id="annotation-count-badge", color="primary", pill=True, className="ms-auto")
                ], className="d-flex align-items-center justify-content-between")
            ], className="border-0", style={"background": "rgba(26, 32, 44, 0.9)"}),
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
                    html.I(className="fas fa-mouse-pointer me-1", style={"color": "#adb5bd"}),
                    html.Span(id="mouse-coords", className="text-muted small")
                ], className="mt-2 px-2")
            ], className="p-3", style={"background": "rgba(45, 55, 72, 0.3)"})
        ], className="border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
    
    def _create_annotations_list(self):
        """Crear la lista de anotaciones"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-tags me-2", style={"color": "#00d4aa"}),
                    "Lista de Anotaciones"
                ], className="mb-0 text-light fw-semibold")
            ], className="border-0", style={"background": "rgba(26, 32, 44, 0.9)"}),
            dbc.CardBody([
                html.Div(id="annotations-list", 
                        style={'max-height': '300px', 'overflow-y': 'auto'})
            ], className="p-3", style={"background": "rgba(45, 55, 72, 0.3)"})
        ], className="mb-4 border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
    
    def _create_configuration_panel(self):
        """Crear el panel de configuración"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-cog me-2", style={"color": "#00d4aa"}),
                    "Configuración"
                ], className="mb-0 text-light fw-semibold")
            ], className="border-0", style={"background": "rgba(26, 32, 44, 0.9)"}),
            dbc.CardBody([
                # Nueva clase para anotaciones
                html.Div([
                    html.Label([
                        html.I(className="fas fa-plus-circle me-2", style={"color": "#00d4aa"}),
                        "Clase para nuevas anotaciones"
                    ], className="mb-2 fw-semibold text-light", style={"font-size": "0.9rem"}),
                    dbc.Select(
                        id="class-selector",
                        options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                        value=0, size="sm", className="mb-4"
                    )
                ]),
                
                # Sección para cambiar clase
                html.Div([
                    html.Label([
                        html.I(className="fas fa-edit me-2", style={"color": "#feca57"}),
                        "Cambiar Clase Seleccionada"
                    ], className="mb-2 fw-semibold text-light", style={"font-size": "0.9rem"}),
                    
                    dbc.Alert(id="selected-info", color="info", className="mb-3 text-center small"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Select(
                                id="selected-class-selector",
                                options=[{"label": cls, "value": i} for i, cls in enumerate(self.classes)],
                                value=0, size="sm", disabled=True
                            )
                        ], width=8),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-check me-1"),
                                "Cambiar"
                            ], id="change-class-button", color="warning", 
                             size="sm", disabled=True, className="w-100")
                        ], width=4)
                    ], className="mb-3"),
                ]),
                
                # Controles de visualización
                html.Div([
                    html.Label([
                        html.I(className="fas fa-eye me-2", style={"color": "#00d4aa"}),
                        "Visualización"
                    ], className="mb-3 fw-semibold text-light", style={"font-size": "0.9rem"}),
                    
                    html.Label("Opacidad:", className="mb-2 text-light small fw-semibold"),
                    dcc.Slider(
                        id="opacity-slider", min=0.1, max=1.0, value=0.3, step=0.1,
                        marks={0.1: {'label': '0.1', 'style': {'color': '#adb5bd'}}, 
                               0.5: {'label': '0.5', 'style': {'color': '#adb5bd'}}, 
                               1.0: {'label': '1.0', 'style': {'color': '#adb5bd'}}}, 
                        className="mb-3"
                    ),
                    
                    dbc.Checklist(
                        options=[
                            {"label": "Mostrar IDs", "value": "show_ids"},
                            {"label": "Mostrar coordenadas", "value": "show_coords"},
                        ],
                        value=["show_ids"], id="display-options", inline=True,
                        className="mb-3"
                    )
                ])
            ], className="p-3", style={"background": "rgba(45, 55, 72, 0.3)"})
        ], className="mb-4 border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
    
    def _create_statistics_panel(self):
        """Crear el panel de estadísticas"""
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className="fas fa-chart-bar me-2", style={"color": "#00d4aa"}),
                    "Estadísticas"
                ], className="mb-0 text-light fw-semibold")
            ], className="border-0", style={"background": "rgba(26, 32, 44, 0.9)"}),
            dbc.CardBody([
                html.Div(id="stats-content")
            ], className="p-3", style={"background": "rgba(45, 55, 72, 0.3)"})
        ], className="border-0", style={"background": "rgba(45, 55, 72, 0.8)"})
    
    def _create_modals(self):
        """Crear los modals"""
        return dbc.Modal([
            dbc.ModalHeader("⚠️ Confirmar Eliminación"),
            dbc.ModalBody("¿Estás seguro de que quieres eliminar todas las anotaciones de este frame?"),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="cancel-delete", color="secondary"),
                dbc.Button("Eliminar Todo", id="confirm-delete", color="danger")
            ])
        ], id="delete-modal", is_open=False)
    
    def _create_toast(self):
        """Crear el toast de notificaciones"""
        return dbc.Toast(
            id="notification-toast", header="Notificación", is_open=False,
            dismissable=True, duration=3000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "z-index": 9999}
        )
    
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
        """Configurar todos los callbacks"""
        self._setup_keyboard_callbacks()
        self._setup_navigation_callbacks()
        self._setup_annotation_callbacks()
        self._setup_interaction_callbacks()
        self._setup_utility_callbacks()
        self._setup_page_callbacks()
    
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
            
            # Card principal para la herramienta de anotación
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("🏷️ Herramienta de Anotación", className="card-title"),
                            html.P("Crea y edita bounding boxes en tus imágenes con una interfaz similar a CVAT"),
                            html.P(f"📁 Dataset activo: {self.dataset_path}"),
                            html.P(f"🖼️ Imágenes disponibles: {len(self.image_files)}"),
                            html.P(f"🏷️ Clases: {', '.join(self.classes)}"),
                            dbc.Button("Abrir Herramienta de Anotación", id="btn-annotation", 
                                     color="primary", size="lg", className="w-100")
                        ])
                    ], className="hover-card mb-4")
                ], md=8, className="mx-auto"),
            ]),
            
            # Información adicional
            dbc.Row([
                dbc.Col([
                    dbc.Alert([
                        html.H4("💡 Atajos de Teclado", className="alert-heading"),
                        html.P("• F: Siguiente imagen"),
                        html.P("• D: Imagen anterior"),  
                        html.P("• Ctrl+Z: Deshacer"),
                        html.P("• Supr: Eliminar anotación seleccionada"),
                    ], color="info", className="mb-4")
                ], md=6),
                dbc.Col([
                    dbc.Alert([
                        html.H4("📊 Estado del Sistema", className="alert-heading"),
                        html.P(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"),
                        html.P("✅ Sistema funcionando correctamente"),
                    ], color="success", className="mb-4")
                ], md=6),
            ])
        ], fluid=True)
    
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
                            if (nextBtn && !nextBtn.disabled) { 
                                nextBtn.click(); 
                                event.preventDefault(); 
                            }
                        } else if (event.key === 'd' || event.key === 'D') {
                            const prevBtn = document.getElementById('prev-button');
                            if (prevBtn && !prevBtn.disabled) { 
                                prevBtn.click(); 
                                event.preventDefault(); 
                            }
                        } else if (event.ctrlKey && (event.key === 'z' || event.key === 'Z')) {
                            const undoBtn = document.getElementById('undo-button');
                            if (undoBtn && !undoBtn.disabled) { 
                                undoBtn.click(); 
                                event.preventDefault(); 
                            }
                        } else if (event.key === 'Delete' || event.key === 'Supr') {
                            const deleteBtn = document.getElementById('delete-selected-button');
                            if (deleteBtn && !deleteBtn.disabled) { 
                                deleteBtn.click(); 
                                event.preventDefault(); 
                            }
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
            [State('current-annotations', 'data')],
            prevent_initial_call=False
        )
        def navigate_and_update_display(next_clicks, prev_clicks, first_clicks, last_clicks, 
                                      reload_clicks, opacity, display_options, current_annotations):
            """Manejar navegación y actualización de display"""
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
            """Actualizar lista de anotaciones"""
            return self._update_annotations_list(annotations)
        
        # Callback para seleccionar anotación desde la lista
        @self.app.callback(
            [Output('selected-annotation', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True)],
            [Input({'type': 'select-btn', 'index': ALL}, 'n_clicks')],
            [State('current-annotations', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def select_annotation_from_list(select_clicks, annotations, opacity, display_options):
            """Seleccionar anotación desde la lista"""
            if not any(select_clicks) or not annotations:
                return no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update
            
            # Obtener el índice del botón presionado
            button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
            selected_idx = button_id['index']
            
            if 0 <= selected_idx < len(annotations):
                # Regenerar la figura con la anotación seleccionada
                current_image = self.image_files[self.current_image_index]
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                
                fig, _ = self.figure_generator.create_figure_with_annotations(
                    current_image, annotations, opacity, show_ids, show_coords, selected_idx
                )
                
                return selected_idx, fig
            
            return no_update, no_update
        
        # Callback para eliminar anotación desde la lista
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input({'type': 'delete-btn', 'index': ALL}, 'n_clicks')],
            [State('current-annotations', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def delete_annotation_from_list(delete_clicks, annotations, opacity, display_options):
            """Eliminar anotación desde la lista"""
            if not any(delete_clicks) or not annotations:
                return no_update, no_update, no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update
            
            # Obtener el índice del botón presionado
            button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
            delete_idx = button_id['index']
            
            if 0 <= delete_idx < len(annotations):
                # Guardar estado para undo
                current_image = self.image_files[self.current_image_index]
                self.undo_manager.push_state(current_image, annotations)
                
                # Eliminar la anotación
                updated_annotations = [ann for i, ann in enumerate(annotations) if i != delete_idx]
                
                # Reindexar IDs
                for i, ann in enumerate(updated_annotations):
                    ann['id'] = i
                
                # Guardar cambios
                self.annotation_manager.save_annotations(current_image, updated_annotations)
                
                # Regenerar figura
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                
                fig, _ = self.figure_generator.create_figure_with_annotations(
                    current_image, updated_annotations, opacity, show_ids, show_coords
                )
                
                class_name = annotations[delete_idx]['class_name']
                message = f"🗑️ Eliminado: {class_name} (ID: {delete_idx})"
                
                return updated_annotations, fig, True, message
            
            return no_update, no_update, no_update, no_update

    def _setup_interaction_callbacks(self):
        """Configurar callbacks de interacción"""
        # Callback principal para manejo de shapes
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
            """Manejar interacción con shapes"""
            return self._handle_shape_interaction_complete(
                relayout_data, annotations, img_dims, image_data, 
                selected_class, opacity, display_options, current_selected
            )

        # Callback para información de anotación seleccionada
        @self.app.callback(
            [Output('selected-info', 'children'),
             Output('selected-class-selector', 'disabled'),
             Output('change-class-button', 'disabled'),
             Output('selected-class-selector', 'value')],
            [Input('selected-annotation', 'data'),
             Input('current-annotations', 'data')]
        )
        def update_selected_info(selected_id, annotations):
            """Actualizar información de selección"""
            return self._update_selected_info(selected_id, annotations)

        # Callback para cambiar clase de anotación seleccionada
        @self.app.callback(
            [Output('current-annotations', 'data', allow_duplicate=True),
             Output('image-graph', 'figure', allow_duplicate=True),
             Output('selected-annotation', 'data', allow_duplicate=True),
             Output('notification-toast', 'is_open', allow_duplicate=True),
             Output('notification-toast', 'children', allow_duplicate=True)],
            [Input('change-class-button', 'n_clicks')],
            [State('selected-annotation', 'data'),
             State('selected-class-selector', 'value'),
             State('current-annotations', 'data'),
             State('opacity-slider', 'value'),
             State('display-options', 'value')],
            prevent_initial_call=True
        )
        def change_selected_class(n_clicks, selected_id, new_class, annotations, opacity, display_options):
            """Cambiar clase de anotación seleccionada"""
            return self._change_selected_class(n_clicks, selected_id, new_class, annotations, opacity, display_options)

        # Callback para deshacer
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
            """Deshacer última acción"""
            return self.callback_manager.handle_undo_action(
                undo_clicks, image_data, opacity, display_options
            )

    def _setup_utility_callbacks(self):
        """Configurar callbacks de utilidades"""
        @self.app.callback(
            Output('stats-content', 'children'),
            [Input('current-annotations', 'data')]
        )
        def update_statistics(annotations):
            """Actualizar estadísticas"""
            return self._update_statistics(annotations)

    def _setup_page_callbacks(self):
        """Configurar callbacks de navegación de páginas"""
        @self.app.callback(
            [Output('page-content', 'children'),
             Output('current-page', 'data')],
            [Input('nav-home', 'n_clicks'),
             Input('nav-annotation', 'n_clicks')],
            [State('current-page', 'data')],
            prevent_initial_call=False
        )
        def navigate_pages(nav_home, nav_annotation, current_page):
            """Manejar la navegación entre páginas"""
            ctx = callback_context
            if not ctx.triggered:
                return self.create_home_page(), {'page': 'home'}
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Navegación
            if button_id == 'nav-home':
                return self.create_home_page(), {'page': 'home'}
            elif button_id == 'nav-annotation':
                return self.create_annotation_page(), {'page': 'annotation'}
            
            # Por defecto, mantener la página actual
            current_page = current_page or {'page': 'home'}
            if current_page['page'] == 'home':
                return self.create_home_page(), current_page
            elif current_page['page'] == 'annotation':
                return self.create_annotation_page(), current_page
            else:
                return self.create_home_page(), {'page': 'home'}
        
        # Callback separado para el botón back-home (solo se activa cuando existe)
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home(back_clicks):
            """Volver al inicio desde la página de anotación"""
            if back_clicks:
                return self.create_home_page(), {'page': 'home'}
            return no_update, no_update
        
        # Callback separado para el botón btn-annotation (solo se activa cuando existe)
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('btn-annotation', 'n_clicks')],
            prevent_initial_call=True
        )
        def open_annotation_tool(btn_clicks):
            """Abrir herramienta de anotación desde el botón en la página de inicio"""
            if btn_clicks:
                return self.create_annotation_page(), {'page': 'annotation'}
            return no_update, no_update
    
    # Métodos de implementación de callbacks
    def _handle_navigation_and_display(self, next_clicks, prev_clicks, first_clicks, last_clicks, 
                                     reload_clicks, opacity, display_options, current_annotations):
        """Implementar navegación y actualización de display"""
        image_changed = False
        
        if callback_context.triggered:
            button_id = callback_context.triggered[0]['prop_id'].split('.')[0]
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
                # Solo actualizar display
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
        
        # Cargar anotaciones si la imagen cambió
        if image_changed:
            annotations = self.annotation_manager.load_annotations(current_image)
        else:
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
                    html.H6("No hay anotaciones", className="mb-1 text-light"),
                    html.Small("Dibuja un rectángulo para crear una nueva", className="text-muted")
                ], className="text-center")
            ], color="dark", className="border-0")]
        
        items = []
        for idx, ann in enumerate(annotations):
            color = self.class_colors[ann['class_id'] % len(self.class_colors)]
            
            items.append(
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.I(className="fas fa-tag me-2", 
                                          style={"color": color, "font-size": "0.9rem"}),
                                    html.Span(ann['class_name'], className="fw-semibold text-light")
                                ], className="d-flex align-items-center mb-1"),
                                html.Small(f"ID: {idx}", className="text-muted", style={"font-size": "0.75rem"}),
                            ], width=6),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-crosshairs")
                                    ], id={"type": "select-btn", "index": idx}, 
                                     size="sm", color="warning", outline=True, 
                                     title="Seleccionar"),
                                    dbc.Button([
                                        html.I(className="fas fa-trash")
                                    ], id={"type": "delete-btn", "index": idx}, 
                                     size="sm", color="danger", outline=True, 
                                     title="Eliminar")
                                ], size="sm")
                            ], width=6, className="text-end")
                        ]),
                    ], className="p-2")
                ], className="mb-2 border-0", 
                   style={
                       "border-left": f"4px solid {color} !important", 
                       "background": "rgba(45, 55, 72, 0.6)"
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
                    html.Span(f"• {class_name}: ", style={"color": "#adb5bd", "font-weight": "bold"}),
                    dbc.Badge(f"{count} ({percentage:.1f}%)", color="info", className="ms-1")
                ])
            )
        
        return stats

    def _handle_shape_interaction_complete(self, relayout_data, annotations, img_dims, image_data, 
                                         selected_class, opacity, display_options, current_selected):
        """Manejar interacción completa con shapes"""
        if not relayout_data:
            return no_update, no_update, False, "", no_update
        
        # Usar el callback_manager para manejar la interacción
        edit_result = self.callback_manager.handle_shape_interaction(
            relayout_data, annotations or [], img_dims, image_data, 
            selected_class, opacity, display_options
        )
        
        return edit_result

    def _update_selected_info(self, selected_id, annotations):
        """Actualizar información de selección"""
        if selected_id is None or not annotations:
            return "🔍 Haz clic en cualquier bounding box para seleccionar", True, True, 0
        
        if 0 <= selected_id < len(annotations):
            selected_ann = annotations[selected_id]
            class_idx = selected_ann.get('class_id', 0)
            class_name = self.classes[class_idx] if class_idx < len(self.classes) else f"Clase {class_idx}"
            
            info_text = f"🎯 Seleccionada: {class_name} (índice: {selected_id})"
            return info_text, False, False, class_idx
        
        return "Anotación no encontrada", True, True, 0

    def _change_selected_class(self, n_clicks, selected_id, new_class, annotations, opacity, display_options):
        """Cambiar clase de anotación seleccionada"""
        if not n_clicks or selected_id is None or not annotations:
            return no_update, no_update, no_update, no_update, no_update
        
        try:
            updated_annotations = annotations.copy()
            if 0 <= selected_id < len(updated_annotations):
                current_image = self.image_files[self.current_image_index]
                
                # Guardar estado para undo
                self.undo_manager.push_state(current_image, annotations)
                
                old_class_name = updated_annotations[selected_id]['class_name']
                new_class = int(new_class)
                
                if 0 <= new_class < len(self.classes):
                    # Actualizar clase
                    updated_annotations[selected_id]['class'] = new_class
                    updated_annotations[selected_id]['class_id'] = new_class
                    updated_annotations[selected_id]['class_name'] = self.classes[new_class]
                    
                    # Guardar cambios
                    self.annotation_manager.save_annotations(current_image, updated_annotations)
                    
                    # Regenerar figura
                    show_ids = 'show_ids' in (display_options or ['show_ids'])
                    show_coords = 'show_coords' in (display_options or [])
                    updated_figure, _ = self.figure_generator.create_figure_with_annotations(
                        current_image, updated_annotations, opacity, show_ids, show_coords, selected_id
                    )
                    
                    success_message = f"✅ Cambiado: {old_class_name} → {self.classes[new_class]}"
                    
                    return updated_annotations, updated_figure, selected_id, True, success_message
                    
        except Exception as e:
            print(f"Error cambiando clase: {e}")
            error_message = f"❌ Error: {str(e)}"
            return no_update, no_update, no_update, True, error_message
        
        return no_update, no_update, no_update, no_update, no_update

def main():
    """Función principal"""
    try:
        # Crear la aplicación completa
        suite = AdvancedAnnotationSuite(app)
        suite.setup_layout()
        suite.setup_callbacks()
        
        print("🚀 Iniciando AutoDistill Suite - Herramienta de Anotación Completa...")
        print(f"📁 Directorio de trabajo: {suite.dataset_path}")
        print(f"📄 Archivo de clases: {suite.classes_yaml}")
        print(f"🖼️ Imágenes encontradas: {len(suite.image_files)}")
        print(f"🏷️ Clases disponibles ({len(suite.classes)}): {', '.join(suite.classes)}")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()