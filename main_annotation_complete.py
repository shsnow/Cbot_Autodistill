import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, clientside_callback, no_update
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import sys
import argparse
import re
import json
import glob

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

app.title = "Cbot Suite - Herramienta de Anotación Completa"

class AdvancedAnnotationSuite:
    def __init__(self, app):
        self.app = app
        
        # Crear carpeta output si no existe
        os.makedirs('output', exist_ok=True)
        
        # Configurar dataset por defecto
        self.dataset_path = "Test_Dataset"
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
                dbc.NavItem(dbc.NavLink("🏛️ Clases", id="nav-classes", href="#")),
                dbc.NavItem(dbc.NavLink("🤖 AutoDistill", id="nav-autodistill", href="#")),
                dbc.NavItem(dbc.NavLink("🧠 Entrenamiento", id="nav-training", href="#")),
                dbc.NavItem(dbc.NavLink("📁 Archivos", id="nav-files", href="#")),
            ],
            brand="Cbot Suite - Herramienta de etiquetado",
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
            
            # Stores para datos de videos (disponibles globalmente)
            dcc.Store(id='videos-data', data=[]),
            dcc.Store(id='videos-refresh', data=0),
            dcc.Store(id='processing-status', data={}),
            
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
        self._setup_files_callbacks()
        self._setup_classes_callbacks()
        self._setup_autodistill_callbacks()
        self._setup_training_callbacks()
    
    def create_home_page(self):
        """Crear la página de inicio"""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 Cbot Suite", className="text-center mb-4"),
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
    
    def create_classes_page(self):
        """Crear la página de gestión de archivos de clases"""
        return dbc.Container([
            # Header de la página
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button("← Volver al Inicio", id="back-home-classes", 
                                 color="secondary", className="mb-3"),
                        html.H2([
                            html.I(className="fas fa-tags me-3", style={"color": "#feca57"}),
                            "Gestión de Archivos de Clases"
                        ], className="mb-4"),
                        html.P("Crea, edita y gestiona archivos de clases para tus proyectos", 
                              className="text-muted mb-4")
                    ])
                ])
            ]),
            
            # Panel de creación de nuevo archivo de clases
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-plus-circle me-2", style={"color": "#48bb78"}),
                                "Crear Nuevo Archivo de Clases"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Nombre del archivo:", className="fw-bold mb-2"),
                                    dbc.Input(
                                        id="new-classes-filename",
                                        placeholder="Ejemplo: vehiculos_urbanos",
                                        className="mb-3"
                                    ),
                                    html.Label("Descripción:", className="fw-bold mb-2"),
                                    dbc.Textarea(
                                        id="new-classes-description",
                                        placeholder="Descripción del conjunto de clases...",
                                        rows=2,
                                        className="mb-3"
                                    )
                                ], md=6),
                                dbc.Col([
                                    html.Label("Clases (una por línea):", className="fw-bold mb-2"),
                                    dbc.Textarea(
                                        id="new-classes-list",
                                        placeholder="person\ncar\nbus\ntruck\nbicycle\nmotorcycle",
                                        rows=8,
                                        className="mb-3"
                                    )
                                ], md=6)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-save me-2"),
                                        "Guardar Archivo de Clases"
                                    ], id="save-classes-file", color="success", 
                                     className="w-100", size="lg")
                                ])
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Lista de archivos de clases existentes
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-list me-2", style={"color": "#00d4aa"}),
                                "Archivos de Clases Existentes"
                            ], className="mb-0"),
                            dbc.Button([
                                html.I(className="fas fa-sync-alt me-1"),
                                "Actualizar"
                            ], id="refresh-classes-list", color="info", 
                             size="sm", className="ms-auto")
                        ], className="d-flex justify-content-between align-items-center"),
                        dbc.CardBody([
                            html.Div(id="classes-files-list", children=[
                                dbc.Alert([
                                    html.I(className="fas fa-info-circle me-2"),
                                    "Cargando archivos de clases..."
                                ], color="info")
                            ])
                        ])
                    ])
                ])
            ]),
            
            # Modal para editar archivo de clases
            dbc.Modal([
                dbc.ModalHeader("Editar Archivo de Clases"),
                dbc.ModalBody([
                    html.Label("Nombre del archivo:", className="fw-bold mb-2"),
                    dbc.Input(id="edit-classes-filename", className="mb-3"),
                    html.Label("Descripción:", className="fw-bold mb-2"),
                    dbc.Textarea(id="edit-classes-description", rows=2, className="mb-3"),
                    html.Label("Clases (una por línea):", className="fw-bold mb-2"),
                    dbc.Textarea(id="edit-classes-list", rows=10, className="mb-3")
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="cancel-edit-classes", color="secondary"),
                    dbc.Button("Guardar Cambios", id="save-edit-classes", color="success")
                ])
            ], id="edit-classes-modal", is_open=False, size="lg"),
            
            # Toast para notificaciones
            dbc.Toast(
                id="classes-toast",
                header="Notificación",
                is_open=False,
                dismissable=True,
                duration=3000,
                style={"position": "fixed", "top": 66, "right": 10, "width": 350}
            )
        ], fluid=True)
    
    def create_files_page(self):
        """Crear la página de gestión de archivos y videos"""
        return dbc.Container([
            # Header de la página
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button("← Volver al Inicio", id="back-home-files", 
                                 color="secondary", className="mb-3"),
                        html.H2([
                            html.I(className="fas fa-video me-3", style={"color": "#00d4aa"}),
                            "Gestión de Videos y Archivos"
                        ], className="mb-4"),
                        html.P("Convierte videos a frames y gestiona tus datasets", 
                              className="text-muted mb-4")
                    ])
                ])
            ]),
            

            
            # Panel de control
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-cog me-2"),
                                "Panel de Control"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-sync me-2"),
                                        "Actualizar Lista"
                                    ], id="refresh-videos-btn", color="primary", 
                                     className="w-100 mb-2")
                                ], md=3),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-folder-open me-2"),
                                        "Abrir Carpeta Videos"
                                    ], id="open-videos-folder-btn", color="info", 
                                     className="w-100 mb-2")
                                ], md=3),
                                dbc.Col([
                                    html.Div([
                                        html.Label("Carpeta de Videos:", className="mb-1"),
                                        dbc.Input(
                                            id="videos-folder-path",
                                            value="videos/",
                                            placeholder="Ruta a la carpeta de videos",
                                            className="mb-2"
                                        )
                                    ])
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Estadísticas
            dbc.Row([
                dbc.Col([
                    dbc.Alert(id="videos-stats", color="info")
                ], md=12)
            ]),
            
            # Lista de videos
            dbc.Row([
                dbc.Col([
                    html.Div(id="videos-grid", children=[
                        dbc.Alert([
                            html.Div([
                                html.I(className="fas fa-video fa-3x mb-3", 
                                      style={"color": "#6c757d"}),
                                html.H5("Cargando videos...", className="text-muted"),
                                html.P("Buscando archivos de video en la carpeta especificada")
                            ], className="text-center")
                        ], color="light")
                    ])
                ])
            ]),
            
            # Toast para notificaciones
            dbc.Toast(
                id="files-toast", header="Notificación", is_open=False,
                dismissable=True, duration=4000,
                style={"position": "fixed", "top": 66, "right": 10, 
                      "width": 350, "z-index": 9999}
            )
            
        ], fluid=True)
    
    def create_autodistill_page(self):
        """Crear la página de AutoDistill para etiquetado automático"""
        return dbc.Container([
            # Header de la página
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Button("← Volver al Inicio", id="back-home-autodistill", 
                                 color="secondary", className="mb-3"),
                        html.H2([
                            html.I(className="fas fa-robot me-3", style={"color": "#00d4aa"}),
                            "AutoDistill - Etiquetado Automático"
                        ], className="mb-4"),
                        html.P("Utiliza IA para etiquetar automáticamente tus imágenes usando modelos base", 
                              className="text-muted mb-4")
                    ])
                ])
            ]),
            
            # Stores para datos de autodistill
            dcc.Store(id='autodistill-datasets', data=[]),
            dcc.Store(id='autodistill-config', data={}),
            dcc.Store(id='autodistill-status', data={'running': False, 'progress': 0}),
            
            # Panel de selección de dataset
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-database me-2", style={"color": "#00d4aa"}),
                                "Selección de Dataset"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Dataset a etiquetar:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="autodistill-dataset-selector",
                                        placeholder="Selecciona un dataset generado...",
                                        className="mb-3"
                                    ),
                                    dbc.Button([
                                        html.I(className="fas fa-sync me-2"),
                                        "Actualizar Lista de Datasets"
                                    ], id="refresh-datasets-btn", color="info", outline=True, 
                                     className="w-100")
                                ], md=6),
                                dbc.Col([
                                    html.Label("Información del Dataset:", className="fw-bold mb-2"),
                                    dbc.Alert(id="autodistill-dataset-info", color="light", className="mb-3"),
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Configuración de Ontología
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-tags me-2", style={"color": "#feca57"}),
                                "Configuración de Ontología"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Modelo Base:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="base-model-selector",
                                        options=[
                                            {"label": "YOLO World (Rápido)", "value": "yolo_world"},
                                            {"label": "Grounding DINO (Preciso)", "value": "grounding_dino"},
                                            {"label": "OWL-ViT (Equilibrado)", "value": "owl_vit"}
                                        ],
                                        value="yolo_world",
                                        className="mb-3"
                                    ),
                                    html.Label("Confianza mínima:", className="fw-bold mb-2"),
                                    dbc.Input(
                                        id="confidence-threshold",
                                        type="number",
                                        value=0.3,
                                        min=0.1,
                                        max=0.9,
                                        step=0.1,
                                        className="mb-3"
                                    )
                                ], md=6),
                                dbc.Col([
                                    html.Label("Nombres de clases (una por línea):", className="fw-bold mb-2"),
                                    dbc.Textarea(
                                        id="ontology-classes",
                                        placeholder="person\ncar\ntraffic light\nstop sign\nbus\ntruck",
                                        value="person\ncar\ntraffic light\nstop sign\nbus\ntruck",
                                        rows=6,
                                        className="mb-3"
                                    )
                                ], md=6)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Descripciones de clases (una por línea, mismo orden):", className="fw-bold mb-2"),
                                    dbc.Textarea(
                                        id="ontology-descriptions",
                                        placeholder="Una persona de cualquier edad\nVehículo automóvil de cuatro ruedas\nSemáforo de tráfico con luces\nSeñal de alto octagonal roja\nVehículo de transporte público\nVehículo pesado de carga",
                                        value="Una persona de cualquier edad\nVehículo automóvil de cuatro ruedas\nSemáforo de tráfico con luces\nSeñal de alto octagonal roja\nVehículo de transporte público\nVehículo pesado de carga",
                                        rows=4,
                                        className="mb-3"
                                    )
                                ], md=12)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Alert([
                                        html.I(className="fas fa-info-circle me-2"),
                                        html.Strong("Tip: "),
                                        "Las descripciones ayudan al modelo a entender mejor qué detectar. Mantén el mismo orden entre clases y descripciones."
                                    ], color="info", className="mb-0")
                                ])
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Panel de Control de Ejecución
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-play me-2", style={"color": "#48bb78"}),
                                "Control de Ejecución"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-robot me-2"),
                                        "Iniciar AutoDistill"
                                    ], id="autodistill-start-btn", color="success", size="lg", 
                                     className="w-100 mb-3", disabled=True),
                                    dbc.Button([
                                        html.I(className="fas fa-stop me-2"),
                                        "Detener Proceso"
                                    ], id="autodistill-stop-btn", color="danger", size="lg", 
                                     className="w-100", disabled=True)
                                ], md=4),
                                dbc.Col([
                                    html.Label("Progreso:", className="fw-bold mb-2"),
                                    dbc.Progress(id="autodistill-progress", value=0, striped=True, 
                                               animated=False, className="mb-3"),
                                    html.Div(id="autodistill-status", className="text-center"),
                                ], md=8)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Resultados
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-pie me-2", style={"color": "#9f7aea"}),
                                "Resultados del Etiquetado"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            html.Div(id="autodistill-results", children=[
                                dbc.Alert([
                                    html.Div([
                                        html.I(className="fas fa-info-circle fa-2x mb-3", 
                                              style={"color": "#6c757d"}),
                                        html.H5("Ejecuta AutoDistill para ver resultados", className="text-muted"),
                                        html.P("Selecciona un dataset, configura la ontología y presiona 'Iniciar AutoDistill'")
                                    ], className="text-center")
                                ], color="light")
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Componente de intervalo para monitorear progreso
            dcc.Interval(
                id='autodistill-progress-interval',
                interval=3000,  # Actualizar cada 3 segundos
                n_intervals=0,
                disabled=True
            ),
            
            # Toast para notificaciones
            dbc.Toast(
                id="autodistill-toast", header="AutoDistill", is_open=False,
                dismissable=True, duration=4000,
                style={"position": "fixed", "top": 66, "right": 10, 
                      "width": 350, "z-index": 9999}
            )
            
        ], fluid=True)
    
    def create_training_page(self):
        """Crear la página de entrenamiento"""
        return dbc.Container([
            # Encabezado
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H2([
                            html.I(className="fas fa-brain me-3", style={"color": "#e74c3c"}),
                            "🧠 Entrenamiento de Modelos YOLO"
                        ], className="text-center mb-4"),
                        dbc.Button("← Volver al Inicio", id="back-home-training", 
                                 color="secondary", size="sm", className="mb-4")
                    ])
                ])
            ]),
            
            # Selección de Dataset
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-database me-2", style={"color": "#3498db"}),
                                "Selección de Dataset"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Dataset disponibles:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="training-dataset-selector",
                                        placeholder="Selecciona un dataset para entrenar...",
                                        className="mb-3"
                                    ),
                                    dbc.Button([
                                        html.I(className="fas fa-sync me-2"),
                                        "Actualizar Lista"
                                    ], id="refresh-training-datasets-btn", color="info", outline=True, 
                                     className="w-100 mb-3")
                                ], md=6),
                                dbc.Col([
                                    html.Label("Información del Dataset:", className="fw-bold mb-2"),
                                    html.Div(id="training-dataset-info", className="mb-3"),
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # División Train/Validation
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-cut me-2", style={"color": "#f39c12"}),
                                "División de Datos"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Porcentaje para Entrenamiento:", className="fw-bold mb-2"),
                                    dcc.Slider(
                                        id="train-split-slider",
                                        min=60,
                                        max=90,
                                        step=5,
                                        value=80,
                                        marks={i: f'{i}%' for i in range(60, 95, 10)},
                                        className="mb-3"
                                    ),
                                    html.Div(id="split-info", className="text-center mb-3")
                                ], md=6),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-random me-2"),
                                        "Dividir Dataset"
                                    ], id="split-dataset-btn", color="warning", size="lg", 
                                     className="w-100 mb-3", disabled=True),
                                    html.Div(id="split-status", className="text-center")
                                ], md=6)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Configuración de Clases para Entrenamiento
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-tags me-2", style={"color": "#e67e22"}),
                                "Configuración de Clases"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Fuente de clases:", className="fw-bold mb-2"),
                                    dbc.RadioItems(
                                        id="classes-source-selector",
                                        options=[
                                            {"label": "🗂️ Usar archivo data.yaml del dataset", "value": "dataset"},
                                            {"label": "📁 Seleccionar archivo de clases personalizado", "value": "custom"},
                                            {"label": "✏️ Escribir clases manualmente", "value": "manual"}
                                        ],
                                        value="dataset",
                                        className="mb-3"
                                    )
                                ], md=12)
                            ]),
                            # Selector de archivo personalizado (oculto por defecto)
                            html.Div([
                                dbc.Row([
                                    dbc.Col([
                                        html.Label("Archivo de clases personalizado:", className="fw-bold mb-2"),
                                        dbc.Select(
                                            id="custom-classes-file-selector",
                                            placeholder="Selecciona un archivo de clases...",
                                            className="mb-3"
                                        ),
                                        dbc.Button([
                                            html.I(className="fas fa-sync me-2"),
                                            "Actualizar Lista de Archivos"
                                        ], id="refresh-classes-files-btn", color="info", outline=True, size="sm")
                                    ], md=6),
                                    dbc.Col([
                                        html.Label("Información del archivo:", className="fw-bold mb-2"),
                                        html.Div(id="selected-classes-file-info", className="mb-3")
                                    ], md=6)
                                ])
                            ], id="custom-classes-section", style={"display": "none"}),
                            # Editor manual de clases (oculto por defecto)
                            html.Div([
                                dbc.Row([
                                    dbc.Col([
                                        html.Label("Clases para entrenamiento (una por línea):", className="fw-bold mb-2"),
                                        dbc.Textarea(
                                            id="manual-training-classes",
                                            placeholder="person\ncar\nbus\ntruck\nbicycle\nmotorcycle\ntraffic light\nstop sign",
                                            rows=8,
                                            className="mb-3"
                                        )
                                    ], md=6),
                                    dbc.Col([
                                        html.Label("Descripción:", className="fw-bold mb-2"),
                                        dbc.Textarea(
                                            id="manual-classes-description",
                                            placeholder="Descripción de las clases seleccionadas para este entrenamiento...",
                                            rows=4,
                                            className="mb-3"
                                        ),
                                        dbc.Alert([
                                            html.I(className="fas fa-info-circle me-2"),
                                            html.Strong("Nota: "),
                                            "Las clases deben coincidir con las del dataset o estar incluidas en las anotaciones."
                                        ], color="info")
                                    ], md=6)
                                ])
                            ], id="manual-classes-section", style={"display": "none"}),
                            # Resumen de clases seleccionadas
                            dbc.Row([
                                dbc.Col([
                                    html.Div(id="training-classes-summary", className="mt-3")
                                ])
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Configuración de Entrenamiento
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-cogs me-2", style={"color": "#9b59b6"}),
                                "Configuración de Entrenamiento"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Modelo Base:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="training-model-selector",
                                        options=[
                                            {"label": "YOLOv8 Nano (yolov8n.pt)", "value": "yolov8n.pt"},
                                            {"label": "YOLOv8 Small (yolov8s.pt)", "value": "yolov8s.pt"},
                                            {"label": "YOLOv8 Medium (yolov8m.pt)", "value": "yolov8m.pt"},
                                            {"label": "YOLOv8 Large (yolov8l.pt)", "value": "yolov8l.pt"},
                                            {"label": "YOLOv8 Extra Large (yolov8x.pt)", "value": "yolov8x.pt"}
                                        ],
                                        value="yolov8n.pt",
                                        className="mb-3"
                                    ),
                                    html.Label("Épocas:", className="fw-bold mb-2"),
                                    dbc.Input(
                                        id="training-epochs",
                                        type="number",
                                        value=100,
                                        min=1,
                                        max=1000,
                                        className="mb-3"
                                    )
                                ], md=4),
                                dbc.Col([
                                    html.Label("Tamaño de Imagen:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="training-img-size",
                                        options=[
                                            {"label": "416x416", "value": 416},
                                            {"label": "512x512", "value": 512},
                                            {"label": "640x640", "value": 640},
                                            {"label": "800x800", "value": 800}
                                        ],
                                        value=640,
                                        className="mb-3"
                                    ),
                                    html.Label("Batch Size:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="training-batch-size",
                                        options=[
                                            {"label": "8", "value": 8},
                                            {"label": "16", "value": 16},
                                            {"label": "32", "value": 32},
                                            {"label": "64", "value": 64}
                                        ],
                                        value=16,
                                        className="mb-3"
                                    )
                                ], md=4),
                                dbc.Col([
                                    html.Label("Learning Rate:", className="fw-bold mb-2"),
                                    dbc.Input(
                                        id="training-lr",
                                        type="number",
                                        value=0.01,
                                        min=0.0001,
                                        max=0.1,
                                        step=0.0001,
                                        className="mb-3"
                                    ),
                                    html.Label("Paciencia (Early Stopping):", className="fw-bold mb-2"),
                                    dbc.Input(
                                        id="training-patience",
                                        type="number",
                                        value=50,
                                        min=10,
                                        max=200,
                                        className="mb-3"
                                    )
                                ], md=4)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Control de Entrenamiento
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-play me-2", style={"color": "#27ae60"}),
                                "Control de Entrenamiento"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-rocket me-2"),
                                        "Iniciar Entrenamiento"
                                    ], id="training-start-btn", color="success", size="lg", 
                                     className="w-100 mb-3", disabled=True),
                                    dbc.Button([
                                        html.I(className="fas fa-stop me-2"),
                                        "Detener Entrenamiento"
                                    ], id="training-stop-btn", color="danger", size="lg", 
                                     className="w-100", disabled=True)
                                ], md=4),
                                dbc.Col([
                                    html.Label("Progreso del Entrenamiento:", className="fw-bold mb-2"),
                                    dbc.Progress(id="training-progress", value=0, striped=True, 
                                               animated=False, className="mb-3"),
                                    html.Div(id="training-status", className="text-center"),
                                ], md=8)
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Resultados del Entrenamiento
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5([
                                html.I(className="fas fa-chart-line me-2", style={"color": "#e67e22"}),
                                "Resultados del Entrenamiento"
                            ], className="mb-0")
                        ]),
                        dbc.CardBody([
                            html.Div(id="training-results", children=[
                                dbc.Alert([
                                    html.Div([
                                        html.I(className="fas fa-info-circle fa-2x mb-3", 
                                              style={"color": "#6c757d"}),
                                        html.H5("Ejecuta el entrenamiento para ver resultados", className="text-muted"),
                                        html.P("Selecciona un dataset, configura los parámetros y presiona 'Iniciar Entrenamiento'")
                                    ], className="text-center")
                                ], color="light")
                            ])
                        ])
                    ], className="mb-4")
                ])
            ]),
            
            # Componentes de estado
            dcc.Store(id='training-data'),
            dcc.Interval(
                id='training-progress-interval',
                interval=2000,  # 2 segundos
                n_intervals=0,
                disabled=True
            ),
            
            # Toast para notificaciones
            dbc.Toast(
                id="training-toast",
                header="Entrenamiento",
                is_open=False,
                dismissable=True,
                duration=4000,
                icon="success",
                style={"position": "fixed", "top": 66, "right": 10, "width": 350, "z-index": 9999}
            )
            
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
             Input('nav-annotation', 'n_clicks'),
             Input('nav-classes', 'n_clicks'),
             Input('nav-autodistill', 'n_clicks'),
             Input('nav-training', 'n_clicks'),
             Input('nav-files', 'n_clicks')],
            [State('current-page', 'data')],
            prevent_initial_call=False
        )
        def navigate_pages(nav_home, nav_annotation, nav_classes, nav_autodistill, nav_training, nav_files, current_page):
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
            elif button_id == 'nav-classes':
                return self.create_classes_page(), {'page': 'classes'}
            elif button_id == 'nav-autodistill':
                return self.create_autodistill_page(), {'page': 'autodistill'}
            elif button_id == 'nav-training':
                return self.create_training_page(), {'page': 'training'}
            elif button_id == 'nav-files':
                return self.create_files_page(), {'page': 'files'}
            
            # Por defecto, mantener la página actual
            current_page = current_page or {'page': 'home'}
            if current_page['page'] == 'home':
                return self.create_home_page(), current_page
            elif current_page['page'] == 'annotation':
                return self.create_annotation_page(), current_page
            elif current_page['page'] == 'classes':
                return self.create_classes_page(), current_page
            elif current_page['page'] == 'autodistill':
                return self.create_autodistill_page(), current_page
            elif current_page['page'] == 'training':
                return self.create_training_page(), current_page
            elif current_page['page'] == 'files':
                return self.create_files_page(), current_page
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
        
        # Callback para volver al inicio desde archivos
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home-files', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home_from_files(back_clicks):
            """Volver al inicio desde la página de archivos"""
            if back_clicks:
                return self.create_home_page(), {'page': 'home'}
            return no_update, no_update
        
        # Callback para volver al inicio desde autodistill
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home-autodistill', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home_from_autodistill(back_clicks):
            """Volver al inicio desde la página de autodistill"""
            if back_clicks:
                return self.create_home_page(), {'page': 'home'}
            return no_update, no_update
        
        # Callback para volver al inicio desde training
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home-training', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home_from_training(back_clicks):
            """Volver al inicio desde la página de training"""
            if back_clicks:
                return self.create_home_page(), {'page': 'home'}
            return no_update, no_update
        
        # Callback para volver al inicio desde clases
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input('back-home-classes', 'n_clicks')],
            prevent_initial_call=True
        )
        def go_back_home_from_classes(back_clicks):
            """Volver al inicio desde la página de clases"""
            if back_clicks:
                return self.create_home_page(), {'page': 'home'}
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

    def _setup_files_callbacks(self):
        """Configurar callbacks para la gestión de archivos"""
        # Importar el procesador de videos
        from utils.video_processor import VideoProcessor
        
        # Callback para cargar videos cuando se actualiza la página o datos
        @self.app.callback(
            [Output('videos-data', 'data'),
             Output('videos-stats', 'children'),
             Output('videos-grid', 'children')],
            [Input('refresh-videos-btn', 'n_clicks'),
             Input('videos-folder-path', 'value'),
             Input('processing-status', 'data')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def load_videos(refresh_clicks, videos_folder, processing_status, current_page):
            """Cargar lista de videos de la carpeta"""
            # Solo ejecutar si estamos en la página de archivos
            if current_page and current_page.get('page') != 'files':
                return no_update, no_update, no_update
            
            try:
                processor = VideoProcessor(videos_folder or "videos")
                videos = processor.get_video_files()
                
                # Expandir videos para incluir subdatasets de AutoDistill
                expanded_videos = self._expand_videos_with_subdatasets(videos)
                
                stats = processor.get_video_stats()
                
                # Generar estadísticas
                stats_content = html.Div([
                    html.H6([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Estadísticas de Videos"
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{len(expanded_videos)}", className="mb-0"),
                                html.Small("Datasets encontrados")
                            ], color="info", className="text-center")
                        ], md=3),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{sum(1 for v in expanded_videos if v.get('has_frames', False))}", className="mb-0"),
                                html.Small("Con frames")
                            ], color="warning", className="text-center")
                        ], md=2),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{self._count_autodistill_labeled(expanded_videos)}", className="mb-0"),
                                html.Small("Etiquetados AI")
                            ], color="info", className="text-center")
                        ], md=2),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{sum(1 for v in expanded_videos if not v.get('has_frames', False))}", className="mb-0"),
                                html.Small("Por procesar")
                            ], color="danger", className="text-center")
                        ], md=2)
                    ])
                ])
                
                # Generar grid de videos
                grid = self._create_videos_grid(expanded_videos, processing_status)
                
                return expanded_videos, stats_content, grid
                
            except Exception as e:
                print(f"Error cargando videos: {e}")
                error_stats = dbc.Alert([
                    html.H6("❌ Error"),
                    html.P(f"Error cargando videos: {str(e)}")
                ], color="danger")
                
                return [], error_stats, []
        
        # Callback separado para cargar videos inicialmente cuando se entra a la página de archivos  
        @self.app.callback(
            [Output('videos-data', 'data', allow_duplicate=True)],
            [Input('current-page', 'data')],
            prevent_initial_call=True
        )
        def load_videos_on_page_load(current_page):
            """Cargar videos cuando se entra a la página de archivos"""
            if not current_page or current_page.get('page') != 'files':
                return [no_update]
                
            try:
                processor = VideoProcessor("videos")  # carpeta por defecto
                videos = processor.get_video_files()
                return [videos]
                
            except Exception as e:
                print(f"Error cargando videos iniciales: {e}")
                return [[]]
        
        # Callback para actualizar componentes visuales cuando cambia videos-data
        @self.app.callback(
            [Output('videos-stats', 'children', allow_duplicate=True),
             Output('videos-grid', 'children', allow_duplicate=True)],
            [Input('videos-data', 'data')],
            [State('current-page', 'data'),
             State('processing-status', 'data')],
            prevent_initial_call=True
        )
        def update_videos_display(videos_data, current_page, processing_status):
            """Actualizar display de videos cuando cambian los datos"""
            # Solo ejecutar si estamos en la página de archivos
            if not current_page or current_page.get('page') != 'files':
                return no_update, no_update
                
            if not videos_data:
                return no_update, no_update
                
            try:
                processor = VideoProcessor("videos")
                stats = processor.get_video_stats()
                
                # Generar estadísticas
                stats_content = html.Div([
                    html.H6([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Estadísticas de Videos"
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{len(videos_data)}", className="mb-0"),
                                html.Small("Videos encontrados")
                            ], color="info", className="text-center")
                        ], md=3),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{sum(1 for v in videos_data if v.get('has_frames', False))}", className="mb-0"),
                                html.Small("Con frames")
                            ], color="warning", className="text-center")
                        ], md=2),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{self._count_autodistill_labeled(videos_data)}", className="mb-0"),
                                html.Small("Etiquetados AI")
                            ], color="info", className="text-center")
                        ], md=2),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(f"{sum(1 for v in videos_data if not v.get('has_frames', False))}", className="mb-0"),
                                html.Small("Por procesar")
                            ], color="danger", className="text-center")
                        ], md=2)
                    ])
                ])
                
                # Generar grid de videos
                grid = self._create_videos_grid(videos_data, processing_status or {})
                
                return stats_content, grid
                
            except Exception as e:
                print(f"Error actualizando display de videos: {e}")
                error_stats = dbc.Alert([
                    html.H6("❌ Error"),
                    html.P(f"Error: {str(e)}")
                ], color="danger")
                
                return error_stats, []
        
        # Callback para convertir video a frames
        @self.app.callback(
            [Output('files-toast', 'is_open'),
             Output('files-toast', 'children'),
             Output('videos-data', 'data', allow_duplicate=True),
             Output('processing-status', 'data', allow_duplicate=True)],
            [Input({'type': 'convert-btn', 'index': ALL}, 'n_clicks')],
            [State('videos-data', 'data'),
             State('videos-folder-path', 'value'),
             State('processing-status', 'data'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def convert_video_to_frames(convert_clicks, videos_data, videos_folder, processing_status, current_page):
            """Convertir video seleccionado a frames"""
            # Solo ejecutar si estamos en la página de archivos
            if current_page and current_page.get('page') != 'files':
                return no_update, no_update, no_update, no_update
            
            # Verificar que no estamos en una página donde no existen estos componentes
            try:
                if not videos_data or not any(convert_clicks):
                    return no_update, no_update, no_update, no_update
            except Exception as e:
                # Si hay error accediendo a los componentes, no hacer nada
                return no_update, no_update, no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update
            
            try:
                # Obtener el índice del video
                button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
                video_idx = button_id['index']
                
                if 0 <= video_idx < len(videos_data):
                    video_info = videos_data[video_idx]
                    processor = VideoProcessor(videos_folder or "videos")
                    
                    # Crear la carpeta output si no existe
                    output_base = os.path.join(os.getcwd(), 'output')
                    os.makedirs(output_base, exist_ok=True)
                    
                    # Extraer frames usando el método original
                    try:
                        result = processor.extract_frames(
                            video_path=video_info['file_path'],
                            output_dir=os.path.join(output_base, video_info['name_without_ext']),
                            frame_interval=15,  # Extraer 1 frame cada 15
                            quality=95,
                            callback=None
                        )
                        
                        if result['success']:
                            success = True
                            frames_count = result['extracted_count']
                            message = f"✅ Extraídos {frames_count} frames en output/{video_info['name_without_ext']}"
                        else:
                            success = False
                            frames_count = 0
                            message = result.get('error', 'Error desconocido')
                            
                    except Exception as extract_error:
                        # Si falla el método original, intentar con el nuevo
                        # Crear la carpeta output si no existe
                        output_base = os.path.join(os.getcwd(), 'output')
                        os.makedirs(output_base, exist_ok=True)
                        
                        success, message, frames_count = processor.extract_frames_simple(
                            video_path=video_info['file_path'],
                            output_folder=os.path.join(output_base, video_info['name_without_ext']),
                            frame_interval=15
                        )
                    
                    if success:
                        # Actualizar datos
                        videos_data[video_idx]['has_frames'] = True
                        videos_data[video_idx]['existing_frames'] = frames_count
                        
                        toast_content = html.Div([
                            html.H6("✅ Conversión Exitosa"),
                            html.P(message)
                        ])
                        
                        return True, toast_content, videos_data, {}
                    else:
                        toast_content = html.Div([
                            html.H6("❌ Error en Conversión"),
                            html.P(message)
                        ])
                        
                        return True, toast_content, no_update, {}
                        
            except Exception as e:
                toast_content = html.Div([
                    html.H6("❌ Error"),
                    html.P(f"Error convirtiendo video: {str(e)}")
                ])
                
                return True, toast_content, no_update, {}
            
            return no_update, no_update, no_update, no_update
        
        # Callback para abrir herramienta de etiquetado
        @self.app.callback(
            [Output('page-content', 'children', allow_duplicate=True),
             Output('current-page', 'data', allow_duplicate=True)],
            [Input({'type': 'review-btn', 'index': ALL}, 'n_clicks')],
            [State('videos-data', 'data'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def open_annotation_tool_for_video(review_clicks, videos_data, current_page):
            """Abrir herramienta de etiquetado para video específico"""
            # Solo ejecutar si estamos en la página de archivos
            if current_page and current_page.get('page') != 'files':
                return no_update, no_update
            
            # Verificar que no estamos en una página donde no existen estos componentes
            try:
                if not videos_data or not any(review_clicks):
                    return no_update, no_update
            except Exception as e:
                # Si hay error accediendo a los componentes, no hacer nada
                return no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update
            
            try:
                # Obtener el índice del video
                button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
                video_idx = button_id['index']
                
                if 0 <= video_idx < len(videos_data):
                    video_info = videos_data[video_idx]
                    
                    # Determinar la carpeta correcta según si es subdataset o no
                    if video_info.get('is_subdataset', False):
                        # Para subdatasets, usar la ruta de imágenes directamente
                        frames_folder = video_info.get('images_path', video_info['path'])
                        print(f"🔄 Cambiando a subdataset: {frames_folder}")
                    else:
                        # Para videos originales, usar la estructura tradicional
                        frames_folder = os.path.join('output', video_info['name_without_ext'])
                        print(f"🔄 Cambiando a dataset: {frames_folder}")
                    
                    # Verificar que la carpeta de frames existe
                    if not os.path.exists(frames_folder):
                        print(f"❌ Error: La carpeta de frames {frames_folder} no existe")
                        return no_update, no_update
                    
                    # Cambiar el dataset path para la herramienta de anotación
                    self.dataset_path = frames_folder
                    
                    # Recargar imágenes y configuración para el nuevo dataset
                    self._reload_dataset_for_folder(frames_folder)
                    
                    # Verificar que hay imágenes
                    if not self.image_files:
                        print(f"❌ Error: No se encontraron imágenes en {frames_folder}")
                        return no_update, no_update
                    
                    print(f"✅ Dataset cargado exitosamente: {len(self.image_files)} imágenes")
                    
                    return self.create_annotation_page(), {'page': 'annotation'}
                        
            except Exception as e:
                print(f"Error abriendo herramienta para video: {e}")
                return no_update, no_update
            
            return no_update, no_update

    def _setup_autodistill_callbacks(self):
        """Configurar callbacks para AutoDistill"""
        from pathlib import Path
        import os
        
        # Callback para cargar datasets disponibles cuando se entra a la página de AutoDistill
        @self.app.callback(
            Output('autodistill-dataset-selector', 'options'),
            [Input('current-page', 'data')],
            prevent_initial_call=True
        )
        def load_available_datasets(current_page):
            """Cargar datasets disponibles desde la carpeta output"""
            if not current_page or current_page.get('page') != 'autodistill':
                return no_update
            
            try:
                output_path = Path('output')
                if not output_path.exists():
                    return []
                
                options = []
                for folder in output_path.iterdir():
                    if folder.is_dir():
                        # Verificar que la carpeta contiene imágenes
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                        has_images = any(
                            any(folder.glob(f'*{ext}')) for ext in image_extensions
                        )
                        
                        if has_images:
                            # Contar imágenes
                            image_count = sum(
                                len(list(folder.glob(f'*{ext}'))) for ext in image_extensions
                            )
                            
                            options.append({
                                'label': f"{folder.name} ({image_count} imágenes)",
                                'value': str(folder)
                            })
                
                return sorted(options, key=lambda x: x['label'])
                
            except Exception as e:
                print(f"Error cargando datasets: {e}")
                return []
        
        # Callback para ejecutar AutoDistill
        @self.app.callback(
            [Output('autodistill-progress', 'value'),
             Output('autodistill-progress', 'label'),
             Output('autodistill-status', 'children'),
             Output('autodistill-results', 'children'),
             Output('autodistill-start-btn', 'disabled'),
             Output('autodistill-stop-btn', 'disabled'),
             Output('autodistill-progress-interval', 'disabled')],
            [Input('autodistill-start-btn', 'n_clicks'),
             Input('autodistill-stop-btn', 'n_clicks')],
            [State('autodistill-dataset-selector', 'value'),
             State('base-model-selector', 'value'),
             State('ontology-classes', 'value'),
             State('confidence-threshold', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def execute_autodistill(start_clicks, stop_clicks, dataset_path, base_model, 
                              ontology_text, confidence_threshold, current_page):
            """Ejecutar proceso de AutoDistill"""
            # Solo ejecutar si estamos en la página correcta
            if not current_page or current_page.get('page') != 'autodistill':
                return no_update, no_update, no_update, no_update, no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update, no_update, no_update
            
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Botón stop presionado
            if triggered_id == 'autodistill-stop-btn':
                return (0, "Detenido", 
                       dbc.Alert("❌ Proceso detenido por el usuario", color="warning"),
                       "", False, True, True)  # Desactivar interval
            
            # Botón start presionado
            if triggered_id == 'autodistill-start-btn' and start_clicks:
                # Validar entradas
                if not dataset_path:
                    return (0, "Error", 
                           dbc.Alert("❌ Por favor selecciona un dataset", color="danger"),
                           "", False, True, True)  # Desactivar interval
                
                if not ontology_text.strip():
                    return (0, "Error", 
                           dbc.Alert("❌ Por favor define las clases en la ontología", color="danger"),
                           "", False, True, True)  # Desactivar interval
                
                try:
                    # Parsear ontología (formato simple: una clase por línea)
                    classes = [line.strip() for line in ontology_text.strip().split('\n') 
                              if line.strip()]
                    
                    if not classes:
                        return (0, "Error", 
                               dbc.Alert("❌ No se encontraron clases válidas en la ontología", color="danger"),
                               "", False, True, True)  # Desactivar interval
                    
                    # Ejecutar AutoDistill real
                    iou_threshold = 0.5  # Valor por defecto
                    return self._run_autodistill_process(
                        dataset_path, base_model, classes, 
                        confidence_threshold, iou_threshold
                    )
                    
                except Exception as e:
                    error_msg = f"Error procesando: {str(e)}"
                    return (0, "Error", 
                           dbc.Alert(f"❌ {error_msg}", color="danger"),
                           "", False, True, True)  # Desactivar interval
            
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        
        # Callback para actualizar información del dataset seleccionado
        @self.app.callback(
            Output('autodistill-dataset-info', 'children'),
            [Input('autodistill-dataset-selector', 'value')],
            prevent_initial_call=True
        )
        def update_dataset_info(dataset_path):
            """Actualizar información del dataset seleccionado"""
            if not dataset_path:
                return ""
            
            try:
                path = Path(dataset_path)
                if not path.exists():
                    return dbc.Alert("❌ Dataset no encontrado", color="danger")
                
                # Contar archivos
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                image_count = sum(
                    len(list(path.glob(f'*{ext}'))) for ext in image_extensions
                )
                
                # Verificar si ya tiene anotaciones
                labels_path = path / 'labels'
                has_labels = labels_path.exists() and any(labels_path.glob('*.txt'))
                label_count = len(list(labels_path.glob('*.txt'))) if has_labels else 0
                
                # Calcular tamaño
                total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                size_mb = total_size / (1024 * 1024)
                
                info = dbc.Card([
                    dbc.CardBody([
                        html.H6(f"📁 {path.name}", className="card-title"),
                        html.P([
                            html.I(className="fas fa-images me-2"),
                            f"{image_count} imágenes"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-tags me-2"),
                            f"{label_count} anotaciones existentes" if has_labels 
                            else "Sin anotaciones previas"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-hdd me-2"),
                            f"{size_mb:.1f} MB"
                        ], className="mb-0")
                    ])
                ], color="light")
                
                return info
                
            except Exception as e:
                return dbc.Alert(f"❌ Error: {str(e)}", color="danger")

        # Callback para controlar estado del botón de inicio
        @self.app.callback(
            Output('autodistill-start-btn', 'disabled', allow_duplicate=True),
            [Input('autodistill-dataset-selector', 'value'),
             Input('ontology-classes', 'value'),
             Input('current-page', 'data')],
            prevent_initial_call=True
        )
        def control_start_button(dataset_path, ontology_text, current_page):
            """Controlar si el botón de inicio debe estar habilitado"""
            if not current_page or current_page.get('page') != 'autodistill':
                return True  # Deshabilitar si no estamos en la página correcta
            
            # Habilitar solo si hay dataset seleccionado y ontología definida
            if dataset_path and ontology_text and ontology_text.strip():
                return False  # Habilitar botón
            else:
                return True   # Deshabilitar botón

        # Callback para monitorear progreso de AutoDistill
        @self.app.callback(
            [Output('autodistill-progress', 'value', allow_duplicate=True),
             Output('autodistill-progress', 'label', allow_duplicate=True),
             Output('autodistill-status', 'children', allow_duplicate=True),
             Output('autodistill-results', 'children', allow_duplicate=True),
             Output('autodistill-progress-interval', 'disabled', allow_duplicate=True),
             Output('autodistill-start-btn', 'disabled', allow_duplicate=True),
             Output('autodistill-stop-btn', 'disabled', allow_duplicate=True)],
            [Input('autodistill-progress-interval', 'n_intervals')],
            [State('autodistill-dataset-selector', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def monitor_autodistill_progress(n_intervals, dataset_path, current_page):
            """Monitorear progreso de AutoDistill"""
            if not current_page or current_page.get('page') != 'autodistill':
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            if not dataset_path:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            try:
                # Verificar si se han generado etiquetas en la carpeta base
                labels_path = Path(dataset_path) / "labels"
                
                if labels_path.exists():
                    label_files = list(labels_path.glob("*.txt"))
                    
                    if label_files:
                        # Contar total de imágenes para calcular progreso
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                        total_images = sum(
                            len(list(Path(dataset_path).glob(f'*{ext}'))) 
                            for ext in image_extensions
                        )
                        
                        progress = min(100, int((len(label_files) / max(total_images, 1)) * 100))
                        
                        if progress >= 100:
                            # Proceso completado y archivos reorganizados
                            results = html.Div([
                                html.H6("✅ AutoDistill Completado"),
                                html.P(f"Se generaron {len(label_files)} anotaciones"),
                                html.P(f"Las etiquetas están disponibles en la pestaña de Archivos"),
                                dbc.Alert([
                                    html.I(className="fas fa-info-circle me-2"),
                                    "Puedes revisar y editar las anotaciones usando el botón 'Ver Etiquetado' en la pestaña de Archivos."
                                ], color="info", className="mt-3")
                            ])
                            
                            status = dbc.Alert([
                                html.I(className="fas fa-check-circle me-2"),
                                "✅ AutoDistill completado y archivos reorganizados"
                            ], color="success")
                            
                            return progress, f"Completado {progress}%", status, results, False, True, True  # Proceso completado, botón start habilitado, stop deshabilitado, interval deshabilitado
                        else:
                            # En progreso
                            status = dbc.Alert([
                                html.I(className="fas fa-cog fa-spin me-2"),
                                f"Procesando... {len(label_files)}/{total_images} imágenes"
                            ], color="info")
                            
                            return progress, f"Progreso {progress}%", status, no_update, no_update, no_update, no_update
                
            except Exception as e:
                print(f"Error monitoreando progreso: {e}")
            
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    def _setup_classes_callbacks(self):
        """Configurar callbacks para la gestión de clases"""
        import os
        import json
        from pathlib import Path
        
        # Crear directorio para archivos de clases si no existe
        classes_dir = Path('classes')
        classes_dir.mkdir(exist_ok=True)
        
        # Callback para guardar nuevo archivo de clases
        @self.app.callback(
            [Output('classes-toast', 'is_open'),
             Output('classes-toast', 'children'),
             Output('new-classes-filename', 'value'),
             Output('new-classes-description', 'value'),
             Output('new-classes-list', 'value')],
            [Input('save-classes-file', 'n_clicks')],
            [State('new-classes-filename', 'value'),
             State('new-classes-description', 'value'),
             State('new-classes-list', 'value')],
            prevent_initial_call=True
        )
        def save_classes_file(save_clicks, filename, description, classes_text):
            """Guardar nuevo archivo de clases"""
            if not save_clicks or not filename or not classes_text:
                return False, "", no_update, no_update, no_update
            
            try:
                # Procesar clases
                classes = [cls.strip() for cls in classes_text.split('\n') if cls.strip()]
                
                if not classes:
                    return True, dbc.Alert("❌ Debe especificar al menos una clase", color="danger"), no_update, no_update, no_update
                
                # Crear estructura del archivo
                classes_data = {
                    "name": filename,
                    "description": description or "",
                    "classes": classes,
                    "created_at": str(datetime.now()),
                    "count": len(classes)
                }
                
                # Guardar archivo
                filepath = classes_dir / f"{filename}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(classes_data, f, ensure_ascii=False, indent=2)
                
                return True, dbc.Alert(f"✅ Archivo '{filename}.json' guardado exitosamente", color="success"), "", "", ""
                
            except Exception as e:
                return True, dbc.Alert(f"❌ Error guardando archivo: {str(e)}", color="danger"), no_update, no_update, no_update
        
        # Callback para cargar lista de archivos de clases
        @self.app.callback(
            Output('classes-files-list', 'children'),
            [Input('current-page', 'data'),
             Input('refresh-classes-list', 'n_clicks'),
             Input('save-classes-file', 'n_clicks')],
            prevent_initial_call=False
        )
        def load_classes_files_list(current_page, refresh_clicks, save_clicks):
            """Cargar y mostrar lista de archivos de clases"""
            if current_page and current_page.get('page') != 'classes':
                return no_update
            
            try:
                classes_files = list(classes_dir.glob("*.json"))
                
                if not classes_files:
                    return [dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        "No hay archivos de clases creados aún. Crea tu primer archivo usando el panel de arriba."
                    ], color="info")]
                
                cards = []
                for file_path in sorted(classes_files):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        cards.append(
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6(data.get('name', file_path.stem), className="card-title"),
                                    html.P(data.get('description', 'Sin descripción'), className="card-text text-muted small"),
                                    html.Div([
                                        html.Small([
                                            html.I(className="fas fa-tags me-1"),
                                            f"{data.get('count', len(data.get('classes', [])))} clases"
                                        ], className="text-muted me-3"),
                                        html.Small([
                                            html.I(className="fas fa-calendar me-1"),
                                            data.get('created_at', 'Fecha desconocida')[:10]
                                        ], className="text-muted")
                                    ], className="mb-3"),
                                    html.Div([
                                        ", ".join(data.get('classes', [])[:5]) + 
                                        ("..." if len(data.get('classes', [])) > 5 else "")
                                    ], className="small text-info mb-3"),
                                    dbc.ButtonGroup([
                                        dbc.Button([
                                            html.I(className="fas fa-edit me-1"),
                                            "Editar"
                                        ], id={'type': 'edit-classes-btn', 'index': file_path.stem}, 
                                         color="warning", size="sm"),
                                        dbc.Button([
                                            html.I(className="fas fa-trash me-1"),
                                            "Eliminar"
                                        ], id={'type': 'delete-classes-btn', 'index': file_path.stem}, 
                                         color="danger", size="sm", outline=True)
                                    ], className="w-100")
                                ])
                            ], className="mb-3")
                        )
                    except Exception as e:
                        print(f"Error cargando {file_path}: {e}")
                        continue
                
                return cards
                
            except Exception as e:
                return [dbc.Alert(f"❌ Error cargando archivos: {str(e)}", color="danger")]

    def _setup_training_callbacks(self):
        """Configurar callbacks para Entrenamiento"""
        from pathlib import Path
        import os
        import shutil
        import random
        
        # Callback para cargar datasets disponibles para entrenamiento
        @self.app.callback(
            Output('training-dataset-selector', 'options'),
            [Input('current-page', 'data'),
             Input('refresh-training-datasets-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def load_training_datasets(current_page, refresh_clicks):
            """Cargar datasets disponibles para entrenamiento"""
            if not current_page or current_page.get('page') != 'training':
                return no_update
            
            try:
                output_path = Path('output')
                if not output_path.exists():
                    return []
                
                options = []
                for folder in output_path.iterdir():
                    if folder.is_dir():
                        # Verificar que la carpeta contiene imágenes y etiquetas
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                        has_images = any(
                            any(folder.glob(f'*{ext}')) for ext in image_extensions
                        )
                        
                        labels_path = folder / 'labels'
                        has_labels = labels_path.exists() and any(labels_path.glob('*.txt'))
                        
                        # Verificar si ya está dividido en train/valid
                        train_path = folder / 'train'
                        valid_path = folder / 'valid'
                        is_split = train_path.exists() and valid_path.exists()
                        
                        if is_split:
                            # Dataset ya dividido - contar imágenes en train y valid
                            train_images = sum(
                                len(list((train_path / 'images').glob(f'*{ext}'))) 
                                for ext in image_extensions
                                if (train_path / 'images').exists()
                            )
                            valid_images = sum(
                                len(list((valid_path / 'images').glob(f'*{ext}'))) 
                                for ext in image_extensions
                                if (valid_path / 'images').exists()
                            )
                            total_images = train_images + valid_images
                            
                            if total_images > 0:
                                options.append({
                                    'label': f"✅ {folder.name} (DIVIDIDO: {train_images} train, {valid_images} valid)",
                                    'value': str(folder)
                                })
                        
                        elif has_images and has_labels:
                            # Dataset sin dividir - contar imágenes y etiquetas
                            image_count = sum(
                                len(list(folder.glob(f'*{ext}'))) for ext in image_extensions
                            )
                            label_count = len(list(labels_path.glob('*.txt')))
                            
                            options.append({
                                'label': f"📂 {folder.name} ({image_count} imágenes, {label_count} etiquetas)",
                                'value': str(folder)
                            })
                
                return sorted(options, key=lambda x: x['label'])
                
            except Exception as e:
                print(f"Error cargando datasets para entrenamiento: {e}")
                return []
        
        # Callback para mostrar información del dataset seleccionado
        @self.app.callback(
            [Output('training-dataset-info', 'children'),
             Output('split-dataset-btn', 'disabled'),
             Output('training-start-btn', 'disabled', allow_duplicate=True)],
            [Input('training-dataset-selector', 'value')],
            prevent_initial_call=True
        )
        def update_training_dataset_info(dataset_path):
            """Actualizar información del dataset para entrenamiento"""
            if not dataset_path:
                return "", True, True
            
            try:
                path = Path(dataset_path)
                if not path.exists():
                    return dbc.Alert("❌ Dataset no encontrado", color="danger"), True, True
                
                # Contar archivos
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                image_count = sum(
                    len(list(path.glob(f'*{ext}'))) for ext in image_extensions
                )
                
                # Verificar etiquetas
                labels_path = path / 'labels'
                has_labels = labels_path.exists() and any(labels_path.glob('*.txt'))
                label_count = len(list(labels_path.glob('*.txt'))) if has_labels else 0
                
                # Verificar si ya está dividido
                train_path = path / 'train'
                val_path = path / 'valid'
                is_split = train_path.exists() and val_path.exists()
                
                # Calcular tamaño
                total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                size_mb = total_size / (1024 * 1024)
                
                info = dbc.Card([
                    dbc.CardBody([
                        html.H6(f"📁 {path.name}", className="card-title"),
                        html.P([
                            html.I(className="fas fa-images me-2"),
                            f"{image_count} imágenes"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-tags me-2"),
                            f"{label_count} etiquetas"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-hdd me-2"),
                            f"{size_mb:.1f} MB"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-cut me-2"),
                            "Ya dividido (train/valid)" if is_split else "Sin dividir"
                        ], className="mb-0", style={"color": "#28a745" if is_split else "#ffc107"})
                    ])
                ], color="light")
                
                # El botón de dividir se habilita solo si no está dividido
                # El botón de entrenar se habilita si está dividido o se puede dividir
                can_split = not is_split and image_count > 0 and label_count > 0
                can_train = is_split or (image_count > 0 and label_count > 0)
                
                return info, not can_split, not can_train
                
            except Exception as e:
                return dbc.Alert(f"❌ Error: {str(e)}", color="danger"), True, True
        
        # Callback para actualizar información de división
        @self.app.callback(
            Output('split-info', 'children'),
            [Input('train-split-slider', 'value'),
             Input('training-dataset-selector', 'value')],
            prevent_initial_call=True
        )
        def update_split_info(train_percent, dataset_path):
            """Actualizar información de división"""
            if not dataset_path:
                return ""
            
            try:
                path = Path(dataset_path)
                if not path.exists():
                    return ""
                
                # Contar imágenes
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                total_images = sum(
                    len(list(path.glob(f'*{ext}'))) for ext in image_extensions
                )
                
                if total_images == 0:
                    return ""
                
                train_count = int(total_images * train_percent / 100)
                val_count = total_images - train_count
                
                return html.Div([
                    html.P(f"📊 Entrenamiento: {train_count} imágenes ({train_percent}%)", className="mb-1"),
                    html.P(f"📊 Validación: {val_count} imágenes ({100-train_percent}%)", className="mb-0")
                ])
                
            except Exception as e:
                return f"Error: {str(e)}"

        # Callback para dividir dataset
        @self.app.callback(
            [Output('training-toast', 'is_open'),
             Output('training-toast', 'children'),
             Output('training-dataset-info', 'children', allow_duplicate=True)],
            [Input('split-dataset-btn', 'n_clicks')],
            [State('training-dataset-selector', 'value'),
             State('train-split-slider', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def split_dataset(n_clicks, dataset_path, train_percent, current_page):
            """Dividir dataset en entrenamiento y validación"""
            if not current_page or current_page.get('page') != 'training':
                return no_update, no_update, no_update
            
            if not n_clicks or not dataset_path:
                return no_update, no_update, no_update
            
            try:
                from pathlib import Path
                import shutil
                import random
                
                base_path = Path(dataset_path)
                if not base_path.exists():
                    return True, dbc.Alert("❌ Dataset no encontrado", color="danger"), no_update
                
                # Crear directorios de destino
                train_dir = base_path / 'train'
                val_dir = base_path / 'valid'
                
                # Crear subdirectorios
                train_images_dir = train_dir / 'images'
                train_labels_dir = train_dir / 'labels'
                val_images_dir = val_dir / 'images'
                val_labels_dir = val_dir / 'labels'
                
                for dir_path in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
                    dir_path.mkdir(parents=True, exist_ok=True)
                
                # Obtener lista de imágenes
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                images = []
                for ext in image_extensions:
                    images.extend(list(base_path.glob(f'*{ext}')))
                
                if not images:
                    return True, dbc.Alert("❌ No se encontraron imágenes en el dataset", color="danger"), no_update
                
                # Mezclar y dividir
                random.shuffle(images)
                train_count = int(len(images) * train_percent / 100)
                train_images = images[:train_count]
                val_images = images[train_count:]
                
                # Mover archivos
                labels_dir = base_path / 'labels'
                moved_train = 0
                moved_val = 0
                
                # Mover imágenes y etiquetas de entrenamiento
                for img_path in train_images:
                    # Mover imagen
                    shutil.move(str(img_path), str(train_images_dir / img_path.name))
                    
                    # Mover etiqueta correspondiente
                    label_name = img_path.stem + '.txt'
                    label_path = labels_dir / label_name
                    if label_path.exists():
                        shutil.move(str(label_path), str(train_labels_dir / label_name))
                    moved_train += 1
                
                # Mover imágenes y etiquetas de validación
                for img_path in val_images:
                    # Mover imagen
                    shutil.move(str(img_path), str(val_images_dir / img_path.name))
                    
                    # Mover etiqueta correspondiente
                    label_name = img_path.stem + '.txt'
                    label_path = labels_dir / label_name
                    if label_path.exists():
                        shutil.move(str(label_path), str(val_labels_dir / label_name))
                    moved_val += 1
                
                # Eliminar carpeta labels original si está vacía
                if labels_dir.exists() and not any(labels_dir.iterdir()):
                    labels_dir.rmdir()
                
                success_message = dbc.Alert([
                    html.H6("✅ Dataset dividido exitosamente", className="mb-2"),
                    html.P(f"📊 Entrenamiento: {moved_train} archivos", className="mb-1"),
                    html.P(f"📊 Validación: {moved_val} archivos", className="mb-0")
                ], color="success")
                
                # Actualizar información del dataset
                updated_info = dbc.Card([
                    dbc.CardBody([
                        html.H6(f"📁 {base_path.name}", className="card-title"),
                        html.P([
                            html.I(className="fas fa-images me-2"),
                            f"{len(images)} imágenes"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-tags me-2"),
                            f"{moved_train + moved_val} etiquetas"
                        ], className="mb-1"),
                        html.P([
                            html.I(className="fas fa-cut me-2"),
                            "Ya dividido (train/valid)"
                        ], className="mb-0", style={"color": "#28a745"})
                    ])
                ], color="light")
                
                return True, success_message, updated_info
                
            except Exception as e:
                error_message = dbc.Alert(f"❌ Error dividiendo dataset: {str(e)}", color="danger")
                return True, error_message, no_update

        # Callback para iniciar entrenamiento
        @self.app.callback(
            [Output('training-toast', 'is_open', allow_duplicate=True),
             Output('training-toast', 'children', allow_duplicate=True),
             Output('training-start-btn', 'disabled', allow_duplicate=True),
             Output('training-stop-btn', 'disabled', allow_duplicate=True),
             Output('training-progress', 'value', allow_duplicate=True),
             Output('training-progress', 'label', allow_duplicate=True),
             Output('training-status', 'children', allow_duplicate=True),
             Output('training-results', 'children', allow_duplicate=True)],
            [Input('training-start-btn', 'n_clicks'),
             Input('training-stop-btn', 'n_clicks')],
            [State('training-dataset-selector', 'value'),
             State('training-epochs', 'value'),
             State('training-batch-size', 'value'),
             State('training-lr', 'value'),
             State('training-img-size', 'value'),
             State('training-patience', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def start_training(start_clicks, stop_clicks, dataset_path, epochs, batch_size, 
                          learning_rate, image_size, patience, current_page):
            """Iniciar o detener el entrenamiento del modelo"""
            if not current_page or current_page.get('page') != 'training':
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            # Botón stop presionado
            if triggered_id == 'training-stop-btn':
                toast_message = dbc.Alert("⏹️ Entrenamiento detenido por el usuario", color="warning")
                return True, toast_message, False, True, 0, "Detenido", "", ""
            
            # Botón start presionado
            if triggered_id == 'training-start-btn' and start_clicks:
                if not dataset_path:
                    toast_message = dbc.Alert("❌ Por favor selecciona un dataset", color="danger")
                    return True, toast_message, False, True, 0, "Error", "", ""
                
                try:
                    from pathlib import Path
                    dataset_path = Path(dataset_path)
                    
                    # Verificar que existan las carpetas train y valid
                    train_dir = dataset_path / 'train'
                    val_dir = dataset_path / 'valid'
                    
                    if not train_dir.exists() or not val_dir.exists():
                        toast_message = dbc.Alert("❌ El dataset no está dividido. Usa 'Dividir Dataset' primero.", color="danger")
                        return True, toast_message, False, True, 0, "Error", "", ""
                    
                    # Verificar que haya imágenes y etiquetas
                    train_images = list(train_dir.glob('images/*.jpg')) + list(train_dir.glob('images/*.png'))
                    train_labels = list(train_dir.glob('labels/*.txt'))
                    
                    if not train_images or not train_labels:
                        toast_message = dbc.Alert("❌ No se encontraron imágenes o etiquetas en train/", color="danger")
                        return True, toast_message, False, True, 0, "Error", "", ""
                    
                    # Iniciar entrenamiento real con YOLOv8
                    return self._start_real_training(
                        dataset_path, epochs, batch_size, learning_rate, 
                        image_size, patience, len(train_images), len(train_labels)
                    )
                    
                except Exception as e:
                    error_msg = f"Error iniciando entrenamiento: {str(e)}"
                    toast_message = dbc.Alert(f"❌ {error_msg}", color="danger")
                    return True, toast_message, False, True, 0, "Error", "", ""
            
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

        # Callback para simular progreso de entrenamiento
        @self.app.callback(
            [Output('training-progress', 'value', allow_duplicate=True),
             Output('training-progress', 'label', allow_duplicate=True),
             Output('training-status', 'children', allow_duplicate=True),
             Output('training-results', 'children', allow_duplicate=True),
             Output('training-toast', 'is_open', allow_duplicate=True),
             Output('training-toast', 'children', allow_duplicate=True),
             Output('training-start-btn', 'disabled', allow_duplicate=True),
             Output('training-stop-btn', 'disabled', allow_duplicate=True)],
            [Input('training-progress-interval', 'n_intervals')],
            [State('training-start-btn', 'disabled'),
             State('training-progress', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def monitor_training_progress(n_intervals, start_disabled, current_progress, current_page):
            """Monitorear progreso real de entrenamiento"""
            if not current_page or current_page.get('page') != 'training':
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            # Solo monitorear si el entrenamiento está activo
            if not start_disabled or current_progress == 0:
                return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            
            # Obtener progreso real del entrenamiento
            if hasattr(self, 'training_progress'):
                progress_data = self.training_progress
                new_progress = progress_data.get('progress', current_progress)
                status = progress_data.get('status', 'training')
                current_epoch = progress_data.get('epoch', 0)
                total_epochs = progress_data.get('total_epochs', 100)
                
                print(f"🔄 Progreso del entrenamiento: {new_progress}% - Época {current_epoch}/{total_epochs}")
                
                # Verificar si hay error
                if status == 'error':
                    error_msg = progress_data.get('error', 'Error desconocido')
                    status_message = dbc.Alert([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"❌ Error: {error_msg}"
                    ], color="danger")
                    
                    toast_message = dbc.Alert(f"❌ Error en el entrenamiento: {error_msg}", color="danger")
                    return (0, "Error", status_message, no_update, 
                           True, toast_message, False, True)
                
            else:
                # Si no hay datos de progreso, usar simulación simple
                new_progress = min(current_progress + 2, 100)
            
            if new_progress < 100 and hasattr(self, 'training_progress') and self.training_progress.get('status') != 'completed':
                # Entrenamiento en progreso
                if hasattr(self, 'training_progress'):
                    current_epoch = self.training_progress.get('epoch', 0)
                    total_epochs = self.training_progress.get('total_epochs', 100)
                    status_text = f"🔥 Entrenando época {current_epoch}/{total_epochs}..."
                else:
                    status_text = f"🔥 Entrenando... {new_progress}%"
                
                status_message = dbc.Alert([
                    html.I(className="fas fa-cog fa-spin me-2"),
                    status_text
                ], color="info")
                
                return (new_progress, f"Entrenando... {new_progress}%", 
                       status_message, no_update, no_update, no_update, no_update, no_update)
            
            elif new_progress < 100:
                # Simulación simple si no hay progreso real
                status_message = dbc.Alert([
                    html.I(className="fas fa-cog fa-spin me-2"),
                    f"🔥 Entrenando... {new_progress}%"
                ], color="info")
                
                return (new_progress, f"Entrenando... {new_progress}%", 
                       status_message, no_update, no_update, no_update, no_update, no_update)
            
            else:
                # Entrenamiento completado - obtener resultados reales
                training_results = getattr(self, 'training_progress', {}).get('results', None)
                
                # Extraer métricas reales si están disponibles
                if training_results and hasattr(training_results, 'metrics'):
                    try:
                        metrics = training_results.metrics
                        precision = f"{metrics.get('precision', [0])[-1]*100:.1f}%" if metrics.get('precision') else "N/A"
                        recall = f"{metrics.get('recall', [0])[-1]*100:.1f}%" if metrics.get('recall') else "N/A"
                        map50 = f"{metrics.get('mAP50', [0])[-1]:.3f}" if metrics.get('mAP50') else "N/A"
                        map50_95 = f"{metrics.get('mAP50-95', [0])[-1]:.3f}" if metrics.get('mAP50-95') else "N/A"
                    except:
                        precision, recall, map50, map50_95 = "N/A", "N/A", "N/A", "N/A"
                else:
                    # Valores por defecto si no hay métricas disponibles
                    precision, recall, map50, map50_95 = "Completado", "Ver terminal", "N/A", "best.pt"
                
                # Obtener información sobre Early Stopping si aplica
                final_epoch = getattr(self, 'training_progress', {}).get('epoch', 0)
                total_epochs = getattr(self, 'training_progress', {}).get('total_epochs', 100)
                
                early_stop_msg = ""
                if final_epoch < total_epochs:
                    early_stop_msg = f" (Early stopping en época {final_epoch}/{total_epochs})"
                
                status_message = dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    f"✅ Entrenamiento completado exitosamente{early_stop_msg}"
                ], color="success")
                
                results_final = html.Div([
                    html.H6("🎯 Resultados del entrenamiento:"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Alert([
                                html.H5(precision, className="mb-0"),
                                html.Small("Precisión final")
                            ], color="success", className="text-center")
                        ], md=3),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(recall, className="mb-0"), 
                                html.Small("Recall promedio")
                            ], color="info", className="text-center")
                        ], md=3),
                        dbc.Col([
                            dbc.Alert([
                                html.H5(map50, className="mb-0"),
                                html.Small("mAP@0.5")
                            ], color="warning", className="text-center")
                        ], md=3),
                        dbc.Col([
                            dbc.Alert([
                                html.H5("best.pt", className="mb-0"),
                                html.Small("Modelo guardado")
                            ], color="primary", className="text-center")
                        ], md=3)
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.P([
                                html.I(className="fas fa-save me-2"),
                                "Modelo entrenado guardado en: ",
                                html.Code("runs/detect/train/weights/best.pt")
                            ], className="mb-1"),
                            html.P([
                                html.I(className="fas fa-clock me-2"),
                                f"Patience configurado: {getattr(self, 'last_patience', 10)} épocas"
                            ], className="mb-1"),
                            html.P([
                                html.I(className="fas fa-info-circle me-2"),
                                "Revisa la terminal para logs detallados del entrenamiento"
                            ], className="mb-0 text-muted")
                        ])
                    ])
                ])
                
                toast_message = dbc.Alert("🎉 ¡Entrenamiento completado exitosamente!", color="success")
                
                return (100, "Completado ✅", status_message, results_final, 
                       True, toast_message, False, True)

    def _validate_and_clean_labels(self, dataset_path):
        """Validar y limpiar las etiquetas del dataset para evitar errores de CUDA"""
        from pathlib import Path
        
        max_class_idx = -1
        corrupted_files = []
        
        # Validar etiquetas de entrenamiento y validación
        for split in ['train', 'valid']:
            labels_dir = dataset_path / split / 'labels'
            if not labels_dir.exists():
                continue
                
            print(f"📝 Validando etiquetas en {split}...")
            label_files = list(labels_dir.glob('*.txt'))
            
            for label_file in label_files:
                try:
                    with open(label_file, 'r') as f:
                        lines = f.readlines()
                    
                    cleaned_lines = []
                    for line_num, line in enumerate(lines):
                        line = line.strip()
                        if not line:
                            continue
                            
                        parts = line.split()
                        if len(parts) < 5:  # class_id x_center y_center width height
                            print(f"⚠️ Línea inválida en {label_file}:{line_num+1}: {line}")
                            continue
                        
                        try:
                            class_id = int(float(parts[0]))
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            # Validar que el class_id esté en rango válido
                            if class_id < 0:
                                print(f"⚠️ Clase negativa en {label_file}:{line_num+1}: {class_id}")
                                continue
                                
                            # Validar que las coordenadas estén entre 0 y 1
                            if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                   0 <= width <= 1 and 0 <= height <= 1):
                                print(f"⚠️ Coordenadas fuera de rango en {label_file}:{line_num+1}: {line}")
                                continue
                            
                            max_class_idx = max(max_class_idx, class_id)
                            cleaned_lines.append(f"{class_id} {x_center} {y_center} {width} {height}\n")
                            
                        except ValueError as e:
                            print(f"⚠️ Error parseando línea en {label_file}:{line_num+1}: {line} - {e}")
                            continue
                    
                    # Escribir las líneas limpias de vuelta al archivo
                    if len(cleaned_lines) != len(lines):
                        print(f"🧹 Limpiando {label_file}: {len(lines)} → {len(cleaned_lines)} líneas")
                        with open(label_file, 'w') as f:
                            f.writelines(cleaned_lines)
                    
                except Exception as e:
                    print(f"❌ Error procesando {label_file}: {e}")
                    corrupted_files.append(str(label_file))
        
        if corrupted_files:
            print(f"⚠️ Se encontraron {len(corrupted_files)} archivos con problemas")
        
        return max_class_idx

    def _start_real_training(self, dataset_path, epochs, batch_size, learning_rate, 
                           image_size, patience, train_images_count, train_labels_count):
        """Iniciar entrenamiento real con YOLOv8"""
        try:
            import threading
            from ultralytics import YOLO
            import yaml
            
            # Crear archivo de configuración del dataset
            data_yaml_path = dataset_path / 'data.yaml'
            
            # Crear configuración YOLO con rutas absolutas
            train_images_path = os.path.abspath(str(dataset_path / 'train' / 'images'))
            valid_images_path = os.path.abspath(str(dataset_path / 'valid' / 'images'))
            
            data_config = {
                'train': train_images_path,
                'val': valid_images_path, 
                'nc': len(self.classes),  # número de clases
                'names': self.classes
            }
            
            # Verificar que las carpetas existan
            if not os.path.exists(train_images_path):
                print(f"❌ Error: No existe la carpeta de entrenamiento: {train_images_path}")
                return
            if not os.path.exists(valid_images_path):
                print(f"❌ Error: No existe la carpeta de validación: {valid_images_path}")
                return
            
            # Guardar configuración
            with open(data_yaml_path, 'w') as f:
                yaml.dump(data_config, f)
            
            print(f"🚀 Iniciando entrenamiento con YOLOv8...")
            print(f"📁 Dataset: {dataset_path}")
            print(f"🖼️ Imágenes de entrenamiento: {train_images_path}")
            print(f"🖼️ Imágenes de validación: {valid_images_path}")
            print(f"🏷️ Clases: {self.classes}")
            print(f"📊 Configuración:")
            print(f"   - Épocas: {epochs}")
            print(f"   - Batch size: {batch_size}")
            print(f"   - Learning rate: {learning_rate}")
            print(f"   - Image size: {image_size}px")
            print(f"   - Train images: {train_images_count}")
            print(f"   - Train labels: {train_labels_count}")
            
            # Validar y limpiar etiquetas antes del entrenamiento
            print("🔍 Validando y limpiando etiquetas del dataset...")
            max_class_idx = self._validate_and_clean_labels(dataset_path)
            
            if max_class_idx >= 0:  # Solo validar si encontramos etiquetas
                if max_class_idx >= len(self.classes):
                    print(f"❌ Error: Se encontraron clases con índice {max_class_idx} pero solo hay {len(self.classes)} clases definidas")
                    print(f"   Clases válidas: {list(range(len(self.classes)))}")
                    print(f"   Nombres de clases: {self.classes}")
                    return
                else:
                    print(f"✅ Etiquetas validadas correctamente")
                    print(f"   - Índice máximo de clase encontrado: {max_class_idx}")
                    print(f"   - Número de clases definidas: {len(self.classes)}")
                    print(f"   - Clases: {self.classes}")
            else:
                print("⚠️ No se encontraron etiquetas válidas en el dataset")
                return
            
            # Inicializar progreso compartido
            if not hasattr(self, 'training_progress'):
                self.training_progress = {'progress': 0, 'status': 'starting', 'epoch': 0, 'loss': 0}
            
            self.training_progress = {
                'progress': 5,
                'status': 'initializing',
                'epoch': 0,
                'loss': 0,
                'total_epochs': epochs
            }
            
            # Guardar patience para mostrar en resultados
            self.last_patience = patience
            
            # Función para entrenar en hilo separado
            def train_model():
                try:
                    import os
                    
                    # Cambiar al directorio del dataset para rutas relativas
                    original_cwd = os.getcwd()
                    os.chdir(dataset_path)
                    
                    # Cargar modelo base
                    model = YOLO(original_cwd + '/yolov8n.pt')
                    
                    self.training_progress.update({
                        'progress': 10,
                        'status': 'training',
                        'epoch': 0
                    })
                    
                    print("🔥 Comenzando entrenamiento...")
                    
                    # Entrenar modelo con ruta relativa
                    results = model.train(
                        data='data.yaml',  # Usar ruta relativa
                        epochs=epochs,
                        imgsz=image_size,
                        batch=batch_size,
                        lr0=learning_rate,
                        patience=patience,
                        save=True,
                        plots=True,
                        verbose=True
                    )
                    
                    # Restaurar directorio original
                    os.chdir(original_cwd)
                    
                    self.training_progress.update({
                        'progress': 100,
                        'status': 'completed',
                        'epoch': epochs,
                        'results': results
                    })
                    
                    print("✅ Entrenamiento completado exitosamente!")
                    
                except Exception as e:
                    print(f"❌ Error durante el entrenamiento: {e}")
                    # Restaurar directorio original en caso de error
                    try:
                        os.chdir(original_cwd)
                    except:
                        pass
                    self.training_progress.update({
                        'progress': 0,
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Iniciar entrenamiento en hilo separado
            training_thread = threading.Thread(target=train_model)
            training_thread.daemon = True
            training_thread.start()
            
            # Mensaje de estado inicial
            status_message = dbc.Alert([
                html.I(className="fas fa-cog fa-spin me-2"),
                f"🚀 Iniciando entrenamiento con {train_images_count} imágenes..."
            ], color="info")
            
            results_info = html.Div([
                html.H6("📊 Configuración del entrenamiento:"),
                html.Ul([
                    html.Li(f"Dataset: {dataset_path.name}"),
                    html.Li(f"Épocas: {epochs}"),
                    html.Li(f"Batch size: {batch_size}"),
                    html.Li(f"Learning rate: {learning_rate}"),
                    html.Li(f"Tamaño de imagen: {image_size}px"),
                    html.Li(f"Imágenes de entrenamiento: {train_images_count}"),
                    html.Li(f"Etiquetas de entrenamiento: {train_labels_count}")
                ])
            ])
            
            toast_message = dbc.Alert("🚀 Entrenamiento iniciado correctamente", color="success")
            
            return (True, toast_message, True, False, 5, "Inicializando... 5%", 
                   status_message, results_info)
                   
        except Exception as e:
            error_msg = f"Error iniciando entrenamiento: {str(e)}"
            print(f"❌ {error_msg}")
            toast_message = dbc.Alert(f"❌ {error_msg}", color="danger")
            return True, toast_message, False, True, 0, "Error", "", ""

        # Callback para manejar selección de fuente de clases en entrenamiento
        @self.app.callback(
            [Output('custom-classes-section', 'style'),
             Output('manual-classes-section', 'style'),
             Output('training-classes-summary', 'children')],
            [Input('classes-source-selector', 'value')],
            prevent_initial_call=True
        )
        def toggle_classes_source(source):
            """Mostrar/ocultar secciones según la fuente de clases seleccionada"""
            if source == "custom":
                return {"display": "block"}, {"display": "none"}, html.Div([
                    dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        "Selecciona un archivo de clases personalizado de la lista."
                    ], color="info")
                ])
            elif source == "manual":
                return {"display": "none"}, {"display": "block"}, html.Div([
                    dbc.Alert([
                        html.I(className="fas fa-edit me-2"),
                        "Escribe las clases manualmente en el campo de texto."
                    ], color="info")
                ])
            else:  # dataset
                return {"display": "none"}, {"display": "none"}, html.Div([
                    dbc.Alert([
                        html.I(className="fas fa-file-code me-2"),
                        "Se usarán las clases del archivo data.yaml del dataset seleccionado."
                    ], color="success")
                ])

    def _create_videos_grid(self, videos, processing_status=None):
        """Crear grid de tarjetas de video"""
        from pathlib import Path
        
        if not videos:
            return []
        
        processing_status = processing_status or {}
        
        cards = []
        for idx, video in enumerate(videos):
            # Verificar si está procesando
            is_processing = processing_status.get(idx, False)
            
            # Verificar si es un subdataset de AutoDistill
            is_subdataset = video.get('is_subdataset', False)
            
            # Determinar botones según el estado
            if is_processing:
                action_buttons = dbc.Button([
                    dbc.Spinner(size="sm", className="me-2"),
                    "Procesando..."
                ], color="info", size="sm", className="w-100", disabled=True)
                
                status_badge = dbc.Badge([
                    html.I(className="fas fa-cog fa-spin me-1"),
                    "Extrayendo frames..."
                ], color="info", className="mb-2")
                
            elif video['has_frames']:
                if is_subdataset:
                    # Para subdatasets de AutoDistill
                    if video.get('has_labels', False):
                        # Subdataset con etiquetas
                        label_count = video.get('label_count', 0)
                        action_buttons = dbc.Button([
                            html.I(className="fas fa-robot me-2"),
                            "Abrir Dataset AI"
                        ], id={'type': 'review-btn', 'index': idx}, 
                         color="info", size="sm", className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-robot me-1"),
                            f"AutoDistill - {video.get('dataset_type', 'Dataset').title()}"
                        ], color="info", className="mb-2")
                    else:
                        # Subdataset solo con imágenes
                        action_buttons = dbc.Button([
                            html.I(className="fas fa-images me-2"),
                            "Ver Imágenes"
                        ], id={'type': 'review-btn', 'index': idx}, 
                         color="secondary", size="sm", className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-images me-1"),
                            f"Solo imágenes - {video.get('dataset_type', 'Dataset').title()}"
                        ], color="secondary", className="mb-2")
                else:
                    # Para videos originales
                    # Verificar si tiene etiquetas de AutoDistill
                    labels_path = Path('output') / video['name_without_ext'] / 'labels'
                    has_autodistill_labels = labels_path.exists() and any(labels_path.glob("*.txt"))
                    
                    if has_autodistill_labels:
                        # Si tiene etiquetas de AutoDistill
                        label_count = len(list(labels_path.glob("*.txt")))
                        action_buttons = dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-eye me-2"),
                                "Ver Etiquetado"
                            ], id={'type': 'review-btn', 'index': idx}, 
                             color="info", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-sync me-2"),
                                "Re-convertir"
                            ], id={'type': 'convert-btn', 'index': idx}, 
                             color="warning", size="sm", outline=True)
                        ], className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-robot me-1"),
                            f"{label_count} etiquetados"
                        ], color="info", className="mb-2")
                    else:
                        # Si solo tiene frames sin etiquetar
                        action_buttons = dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-tag me-2"),
                                "Revisar"
                            ], id={'type': 'review-btn', 'index': idx}, 
                             color="success", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-sync me-2"),
                                "Re-convertir"
                            ], id={'type': 'convert-btn', 'index': idx}, 
                             color="warning", size="sm", outline=True)
                        ], className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-check me-1"),
                            f"{video.get('existing_frames', '0')} frames"
                        ], color="success", className="mb-2")
            else:
                action_buttons = dbc.Button([
                    html.I(className="fas fa-play me-2"),
                    "Convertir a Frames"
                ], id={'type': 'convert-btn', 'index': idx}, 
                 color="primary", size="sm", className="w-100")
                
                status_badge = dbc.Badge([
                    html.I(className="fas fa-clock me-1"),
                    "Sin procesar"
                ], color="warning", className="mb-2")
            
            # Crear tarjeta
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        # Status badge
                        html.Div([status_badge], className="text-center"),
                        
                        # Información del video
                        html.H6(video['name'], className="card-title text-truncate", 
                               title=video['name']),
                        
                        html.Div([
                            html.Small([
                                html.I(className="fas fa-clock me-1"),
                                video.get('duration_str', 'N/A')
                            ], className="text-muted d-block"),
                            html.Small([
                                html.I(className="fas fa-expand-arrows-alt me-1"),
                                video.get('resolution', 'N/A')
                            ], className="text-muted d-block"),
                            html.Small([
                                html.I(className="fas fa-hdd me-1"),
                                video.get('file_size_str', 'N/A')
                            ], className="text-muted d-block"),
                            html.Small([
                                html.I(className="fas fa-film me-1"),
                                f"{video.get('frame_count', 0)} frames"
                            ], className="text-muted d-block")
                        ], className="mb-2"),
                        
                        # Selector de archivo de clases
                        html.Div([
                            html.Label([
                                html.I(className="fas fa-tags me-1"),
                                "Archivo de clases:"
                            ], className="small fw-bold text-muted"),
                            dbc.Select(
                                id={'type': 'classes-selector', 'index': idx},
                                options=[
                                    {"label": "Usar data.yaml por defecto", "value": "default"},
                                    {"label": "Cargar archivos de clases...", "value": "loading"}
                                ],
                                value="default",
                                size="sm",
                                className="mb-2"
                            )
                        ], className="mb-3"),
                        
                        # Botones de acción
                        action_buttons
                        
                    ], className="p-3")
                ], className="h-100 border-0 shadow-sm hover-card",
                   style={"background": "rgba(45, 55, 72, 0.8)"})
            ], md=6, lg=4, xl=3, className="mb-3")
            
            cards.append(card)
        
        return dbc.Row(cards)

    def _count_autodistill_labeled(self, videos):
        """Contar cuántos videos tienen etiquetas de AutoDistill"""
        from pathlib import Path
        
        count = 0
        for video in videos:
            if video.get('is_subdataset'):
                # Para subdatasets, verificar si tiene etiquetas
                if video.get('has_labels', False):
                    count += 1
            elif video.get('has_frames', False):
                # Para videos originales, verificar AutoDistill
                labels_path = Path('output') / video['name_without_ext'] / 'labels'
                if labels_path.exists() and any(labels_path.glob("*.txt")):
                    count += 1
        return count

    def _expand_videos_with_subdatasets(self, videos):
        """Expandir lista de videos para incluir subdatasets de AutoDistill"""
        from pathlib import Path
        
        expanded_videos = []
        
        for video in videos:
            # Agregar el video original
            expanded_videos.append(video)
            
            # Buscar subdatasets de AutoDistill
            video_folder = Path('output') / video['name_without_ext']
            if video_folder.exists():
                # Buscar subcarpetas train, valid, test
                for subdir in ['train', 'valid', 'test']:
                    subdir_path = video_folder / subdir
                    if subdir_path.exists():
                        # Verificar si tiene imágenes
                        images_path = subdir_path / 'images'
                        labels_path = subdir_path / 'labels'
                        
                        has_images = False
                        has_labels = False
                        image_count = 0
                        
                        if images_path.exists():
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            for ext in image_extensions:
                                images = list(images_path.glob(f'*{ext}'))
                                image_count += len(images)
                            has_images = image_count > 0
                        
                        label_count = 0
                        if labels_path.exists():
                            labels = list(labels_path.glob('*.txt'))
                            has_labels = len(labels) > 0
                            label_count = len(labels)
                        
                        if has_images or has_labels:
                            # Crear entrada para el subdataset
                            subdataset = {
                                'name': f"{video['name_without_ext']} - {subdir.title()}",
                                'name_without_ext': f"{video['name_without_ext']}_{subdir}",
                                'path': str(subdir_path),
                                'images_path': str(images_path) if has_images else str(subdir_path),
                                'labels_path': str(labels_path) if has_labels else None,
                                'size': video.get('size', 'N/A'),
                                'duration': f"{image_count} imágenes, {label_count} etiquetas",
                                'has_frames': has_images,
                                'has_labels': has_labels,
                                'label_count': label_count,
                                'is_subdataset': True,
                                'parent_video': video['name_without_ext'],
                                'dataset_type': subdir
                            }
                            expanded_videos.append(subdataset)
        
        return expanded_videos

    def _has_autodistill_labels(self, video_info):
        """Verificar si un video tiene etiquetas de AutoDistill"""
        from pathlib import Path
        
        frames_path = Path('output') / video_info['name_without_ext']
        labels_path = frames_path / 'labels'
        
        return labels_path.exists() and any(labels_path.glob('*.txt'))

    def _reload_dataset_for_folder(self, folder_path):
        """Recargar dataset para una carpeta específica"""
        try:
            # Actualizar ruta del dataset
            self.dataset_path = folder_path
            
            # Recargar imágenes
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            self.image_files = []
            
            if os.path.exists(folder_path):
                for ext in image_extensions:
                    pattern = os.path.join(folder_path, f"*{ext}")
                    files = sorted(glob.glob(pattern, recursive=False))
                    self.image_files.extend([os.path.basename(f) for f in files])
            
            # Resetear índice
            self.current_image_index = 0
            
            # Recargar configuración de anotaciones y figure generator para la nueva ruta
            if hasattr(self, 'annotation_manager'):
                # Determinar la ruta de etiquetas correcta
                # Si estamos en una subcarpeta de AutoDistill (ej: train/images), 
                # las etiquetas están en el directorio hermano 'labels'
                if folder_path.endswith('images'):
                    # Estructura de AutoDistill: train/images -> train/labels
                    parent_dir = os.path.dirname(folder_path)
                    labels_path = os.path.join(parent_dir, 'labels')
                else:
                    # Estructura tradicional: frames -> frames/labels
                    labels_path = os.path.join(folder_path, 'labels')
                
                os.makedirs(labels_path, exist_ok=True)
                self.annotation_manager.labels_path = labels_path
                print(f"📁 Ruta de etiquetas configurada: {labels_path}")
            
            if hasattr(self, 'figure_generator'):
                # Actualizar la ruta en el figure generator
                self.figure_generator.images_path = folder_path
            
            print(f"✅ Dataset recargado: {len(self.image_files)} imágenes en {folder_path}")
            print(f"✅ Archivos encontradas: {self.image_files[:5]}...")  # Mostrar primeros 5
            
        except Exception as e:
            print(f"Error recargando dataset: {e}")

    def _run_autodistill_process(self, dataset_path, base_model, classes, confidence_threshold, iou_threshold):
        """Ejecutar proceso real de AutoDistill"""
        try:
            from autodistill.detection import CaptionOntology
            from autodistill_grounding_dino import GroundingDINO
            from autodistill_yolov8 import YOLOv8
            from pathlib import Path
            import threading
            import time
            
            # Crear ontología
            ontology_dict = {class_name: class_name for class_name in classes}
            ontology = CaptionOntology(ontology_dict)
            
            # Configurar modelo base
            if base_model == "grounding-dino":
                base_model_instance = GroundingDINO(ontology=ontology)
            else:
                # Por defecto usar GroundingDINO
                base_model_instance = GroundingDINO(ontology=ontology)
            
            # Configurar modelo objetivo (YOLOv8)
            target_model = YOLOv8("yolov8n.pt")
            
            # Preparar rutas
            dataset_path = Path(dataset_path)
            labels_dir = dataset_path / "labels"
            labels_dir.mkdir(exist_ok=True)
            
            # Progreso inicial
            progress_value = 20
            status = dbc.Alert([
                html.I(className="fas fa-robot me-2"),
                f"Generando anotaciones con {base_model}..."
            ], color="info")
            
            # Función para ejecutar en thread separado
            def run_distillation():
                try:
                    print(f"🤖 Iniciando AutoDistill en {dataset_path}")
                    print(f"📝 Clases: {classes}")
                    
                    # Ejecutar AutoDistill
                    base_model_instance.label(
                        input_folder=str(dataset_path),
                        output_folder=str(labels_dir),
                        extension=".jpg"
                    )
                    
                    print("✅ AutoDistill completado exitosamente")
                    
                    # Mover archivos de etiquetas a la estructura original
                    self._move_autodistill_labels_to_base(dataset_path, labels_dir)
                    
                except Exception as e:
                    print(f"❌ Error en AutoDistill: {e}")
            
            # Iniciar en thread separado (para no bloquear la UI)
            thread = threading.Thread(target=run_distillation)
            thread.start()
            
            # Simular progreso mientras procesa
            results = html.Div([
                html.H6("🤖 AutoDistill en ejecución:"),
                html.Ul([
                    html.Li(f"Dataset: {dataset_path.name}"),
                    html.Li(f"Modelo base: {base_model}"),
                    html.Li(f"Clases: {', '.join(classes)}"),
                    html.Li(f"Confianza mínima: {confidence_threshold}"),
                    html.Li(f"Directorio de salida: {labels_dir}")
                ]),
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "El proceso puede tardar varios minutos dependiendo del número de imágenes."
                ], color="info", className="mt-3")
            ])
            
            return (progress_value, f"Procesando... {progress_value}%", 
                   status, results, True, False, False)  # Activar interval
            
        except ImportError as e:
            error_msg = f"Error importando módulos de AutoDistill: {str(e)}"
            print(f"❌ {error_msg}")
            return (0, "Error", 
                   dbc.Alert(f"❌ {error_msg}", color="danger"),
                   "", False, True, True)  # Desactivar interval
        except Exception as e:
            error_msg = f"Error ejecutando AutoDistill: {str(e)}"
            print(f"❌ {error_msg}")
            return (0, "Error", 
                   dbc.Alert(f"❌ {error_msg}", color="danger"),
                   "", False, True, True)  # Desactivar interval

    def _move_autodistill_labels_to_base(self, dataset_path, labels_dir):
        """Mover etiquetas de AutoDistill a la estructura original"""
        try:
            import os
            import shutil
            from pathlib import Path
            
            dataset_path = Path(dataset_path)
            labels_dir = Path(labels_dir)
            
            print(f"🔄 Reorganizando archivos de AutoDistill...")
            print(f"📁 Dataset base: {dataset_path}")
            print(f"📂 Directorio de labels: {labels_dir}")
            
            # Buscar carpetas train/labels y valid/labels (estructura típica de AutoDistill)
            train_labels_dir = labels_dir / "train" / "labels"
            valid_labels_dir = labels_dir / "valid" / "labels"
            
            # También buscar estructura alternativa con annotations
            train_annotations_dir = labels_dir / "train" / "annotations"
            valid_annotations_dir = labels_dir / "valid" / "annotations"
            annotations_dir = labels_dir / "annotations"
            
            # Lista de directorios donde buscar etiquetas
            label_sources = []
            
            if train_labels_dir.exists():
                label_sources.append(train_labels_dir)
                print(f"✅ Encontradas etiquetas de entrenamiento en: {train_labels_dir}")
                
            if valid_labels_dir.exists():
                label_sources.append(valid_labels_dir)
                print(f"✅ Encontradas etiquetas de validación en: {valid_labels_dir}")
                
            if train_annotations_dir.exists():
                label_sources.append(train_annotations_dir)
                print(f"✅ Encontradas anotaciones de entrenamiento en: {train_annotations_dir}")
                
            if valid_annotations_dir.exists():
                label_sources.append(valid_annotations_dir)
                print(f"✅ Encontradas anotaciones de validación en: {valid_annotations_dir}")
                
            if annotations_dir.exists():
                label_sources.append(annotations_dir)
                print(f"✅ Encontradas anotaciones en: {annotations_dir}")
            
            # Si no hay directorios específicos, buscar directamente en labels
            if not label_sources and labels_dir.exists():
                if any(labels_dir.glob("*.txt")):
                    label_sources.append(labels_dir)
                    print(f"✅ Encontradas etiquetas directamente en: {labels_dir}")
            
            if not label_sources:
                print("❌ No se encontraron anotaciones de AutoDistill")
                return
            
            # Crear carpeta labels en el directorio base si no existe
            base_labels_dir = dataset_path / "labels"
            base_labels_dir.mkdir(exist_ok=True)
            
            # Mover archivos de etiquetas (.txt) desde todos los directorios encontrados
            moved_count = 0
            for source_dir in label_sources:
                print(f"🔄 Procesando etiquetas desde: {source_dir}")
                for label_file in source_dir.glob("*.txt"):
                    dest_file = base_labels_dir / label_file.name
                    try:
                        # Solo copiar si no existe o si es diferente
                        if not dest_file.exists():
                            shutil.copy2(label_file, dest_file)
                            moved_count += 1
                            print(f"📝 Movido: {label_file.name}")
                        else:
                            print(f"⚠️ Ya existe: {label_file.name}")
                    except Exception as e:
                        print(f"❌ Error moviendo {label_file.name}: {e}")
            
            # Buscar y mover imágenes si están en carpetas separadas
            train_images_dir = labels_dir / "train" / "images"
            valid_images_dir = labels_dir / "valid" / "images"
            
            for images_dir in [train_images_dir, valid_images_dir]:
                if images_dir.exists():
                    print(f"🖼️ Encontradas imágenes en: {images_dir}")
                    for img_file in images_dir.glob("*"):
                        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                            dest_file = dataset_path / img_file.name
                            if not dest_file.exists():  # Solo mover si no existe
                                try:
                                    shutil.copy2(img_file, dest_file)
                                    print(f"🖼️ Movida imagen: {img_file.name}")
                                except Exception as e:
                                    print(f"❌ Error moviendo imagen {img_file.name}: {e}")
            
            # Limpiar carpetas temporales de AutoDistill
            try:
                if labels_dir.exists() and labels_dir != base_labels_dir:
                    shutil.rmtree(labels_dir)
                    print(f"🗑️ Eliminada carpeta temporal: {labels_dir}")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar carpeta temporal: {e}")
            
            print(f"✅ Reorganización completada. {moved_count} etiquetas movidas.")
            
        except Exception as e:
            print(f"❌ Error reorganizando archivos: {e}")

    # Funciones auxiliares para gestión de archivos de clases
    def _load_classes_files(self):
        """Cargar lista de archivos de clases disponibles"""
        classes_folder = "classes_files"
        if not os.path.exists(classes_folder):
            os.makedirs(classes_folder)
            return []
        
        classes_files = []
        for filename in os.listdir(classes_folder):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(classes_folder, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        classes_files.append({
                            'filename': filename,
                            'name': data.get('name', filename.replace('.json', '')),
                            'description': data.get('description', ''),
                            'classes': data.get('classes', []),
                            'created': data.get('created', 'Fecha desconocida')
                        })
                except Exception as e:
                    print(f"Error cargando archivo de clases {filename}: {e}")
        
        return sorted(classes_files, key=lambda x: x['name'])
    
    def _save_classes_file(self, name, description, classes_list):
        """Guardar un nuevo archivo de clases"""
        try:
            classes_folder = "classes_files"
            if not os.path.exists(classes_folder):
                os.makedirs(classes_folder)
            
            # Limpiar el nombre para el archivo
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
            filename = f"{safe_name}.json"
            filepath = os.path.join(classes_folder, filename)
            
            # Crear el contenido del archivo
            data = {
                'name': name,
                'description': description,
                'classes': [cls.strip() for cls in classes_list if cls.strip()],
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0'
            }
            
            # Guardar el archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True, f"Archivo de clases '{name}' guardado correctamente"
        
        except Exception as e:
            return False, f"Error guardando archivo: {str(e)}"
    
    def _get_classes_file_options(self):
        """Obtener opciones para selectores de archivos de clases"""
        classes_files = self._load_classes_files()
        
        options = [{"label": "Usar data.yaml por defecto", "value": "default"}]
        
        for file_data in classes_files:
            options.append({
                "label": f"📁 {file_data['name']} ({len(file_data['classes'])} clases)",
                "value": file_data['filename']
            })
        
        return options

def main():
    """Función principal"""
    try:
        # Crear la aplicación completa
        suite = AdvancedAnnotationSuite(app)
        suite.setup_layout()
        suite.setup_callbacks()

        print("🚀 Iniciando Cbot Suite - Herramienta de Anotación Completa...")
        print(f"📁 Directorio de trabajo: {suite.dataset_path}")
        print(f"📄 Archivo de clases: {suite.classes_yaml}")
        print(f"🖼️ Imágenes encontradas: {len(suite.image_files)}")
        print(f"🏷️ Clases disponibles ({len(suite.classes)}): {', '.join(suite.classes)}")
        print("🌐 Abriendo en: http://localhost:8050")
        print("✅ Aplicación lista!")
        
        # Ejecutar la aplicación
        app.run(
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