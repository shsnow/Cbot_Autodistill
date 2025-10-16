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
        classes_list = self.config_loader.get_classes()
        
        # Convertir la lista de clases a diccionario para consistencia
        self.classes = {i: class_name for i, class_name in enumerate(classes_list)}
        
        # Actualizar el config_loader con el diccionario para consistencia
        self.config_loader.classes = self.classes
        self.config_loader.classes_list = classes_list
        
        self.class_colors = self.config_loader.get_colors(len(classes_list))
        
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
    
    def _get_classes_options(self):
        """Cargar opciones de archivos de clases disponibles"""
        from pathlib import Path
        import json
        
        try:
            classes_dir = Path('classes')
            if not classes_dir.exists():
                return [{"label": "Usar data.yaml por defecto", "value": "default"}]
            
            # Opciones base
            options = [{"label": "Usar data.yaml por defecto", "value": "default"}]
            
            # Cargar archivos de clases
            classes_files = list(classes_dir.glob("*.json"))
            for file_path in sorted(classes_files):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    options.append({
                        "label": f"📁 {data.get('name', file_path.stem)} ({len(data.get('classes', []))} clases)",
                        "value": file_path.name
                    })
                except Exception as e:
                    print(f"Error cargando {file_path}: {e}")
                    continue
            
            return options
            
        except Exception as e:
            print(f"Error cargando opciones de clases: {e}")
            return [{"label": "Usar data.yaml por defecto", "value": "default"}]
    
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
                        options=[{"label": cls_name, "value": cls_id} for cls_id, cls_name in self.classes.items()],
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
                                options=[{"label": cls_name, "value": cls_id} for cls_id, cls_name in self.classes.items()],
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
        self._setup_dataset_merge_callbacks()
    
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
                            html.P(f"🏷️ Clases: {', '.join(self.classes.values())}"),
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
                                ], md=2),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-folder-open me-2"),
                                        "Abrir Carpeta Videos"
                                    ], id="open-videos-folder-btn", color="info", 
                                     className="w-100 mb-2")
                                ], md=2),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-plus me-2"),
                                        "Agregar Videos"
                                    ], id="add-videos-btn", color="success", 
                                     className="w-100 mb-2")
                                ], md=2),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-check-square me-2"),
                                        "Seleccionar Varios Datasets"
                                    ], id="multi-select-btn", color="warning", 
                                     className="w-100 mb-2")
                                ], md=2),
                                dbc.Col([
                                    dbc.Button([
                                        html.I(className="fas fa-layer-group me-2"),
                                        "Unir Datasets Seleccionados"
                                    ], id="merge-datasets-btn", color="danger", 
                                     className="w-100 mb-2", disabled=True)
                                ], md=2)
                            ]),
                            dbc.Row([
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
            
            # Componente de carga de videos (oculto)
            dcc.Upload(
                id="video-upload",
                children=[],
                style={'display': 'none'},
                multiple=True,
                accept='.mp4,.avi,.mov,.mkv,.wmv,.flv,.webm,.m4v'
            ),
            
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
            ),
            
            # Modal para configuración de unión de datasets
            dbc.Modal([
                dbc.ModalHeader([
                    html.H4([
                        html.I(className="fas fa-layer-group me-2"),
                        "Configuración de Unión de Datasets"
                    ])
                ]),
                dbc.ModalBody([
                    # Nombre del nuevo dataset
                    html.Div([
                        html.Label("Nombre del nuevo dataset:", className="fw-bold mb-2"),
                        dbc.Input(
                            id="merge-name",
                            placeholder="Ej: Mi_Dataset_Combinado",
                            className="mb-2"
                        ),
                        html.Small(id="merge-name-validation", className="text-muted")
                    ], className="mb-4"),
                    
                    # Método de renombrado
                    html.Div([
                        html.Label("Método de Renombrado de Archivos:", className="fw-bold mb-2"),
                        dbc.RadioItems(
                            id="rename-strategy",
                            options=[
                                {
                                    "label": [
                                        html.Div([
                                            html.Strong("Secuencial Numérico"),
                                            html.Br(),
                                            html.Small("(ej: 000001.jpg, 000002.txt) Ideal para crear un dataset limpio y ordenado", 
                                                     className="text-muted")
                                        ])
                                    ],
                                    "value": "sequential"
                                },
                                {
                                    "label": [
                                        html.Div([
                                            html.Strong("Prefijo del Dataset Original"),
                                            html.Br(),
                                            html.Small("(ej: dataset_perros_frame_15.jpg) Útil para mantener la trazabilidad del origen", 
                                                     className="text-muted")
                                        ])
                                    ],
                                    "value": "prefix"
                                }
                            ],
                            value="sequential",
                            className="mb-3"
                        )
                    ], className="mb-4"),
                    
                    # Acción sobre datasets originales
                    html.Div([
                        html.Label("Acción sobre los Datasets Originales:", className="fw-bold mb-2"),
                        dbc.RadioItems(
                            id="merge-action",
                            options=[
                                {
                                    "label": [
                                        html.Div([
                                            html.Strong("Copiar (Recomendado)", style={"color": "#28a745"}),
                                            html.Br(),
                                            html.Small("Mantiene los datasets originales intactos", 
                                                     className="text-muted")
                                        ])
                                    ],
                                    "value": "copy"
                                },
                                {
                                    "label": [
                                        html.Div([
                                            html.Strong("Mover", style={"color": "#dc3545"}),
                                            html.Br(),
                                            html.Small("Transfiere los archivos y elimina las carpetas originales. ¡Acción destructiva!", 
                                                     className="text-danger")
                                        ])
                                    ],
                                    "value": "move"
                                }
                            ],
                            value="copy",
                            className="mb-3"
                        )
                    ], className="mb-4"),
                    
                    # Resumen dinámico
                    dbc.Alert(
                        id="merge-summary",
                        color="info",
                        children="Selecciona datasets para ver el resumen..."
                    ),
                    
                    # Progreso de la operación (oculto inicialmente)
                    html.Div([
                        html.H6("Progreso de la unión:", className="mt-3 mb-2"),
                        dbc.Progress(
                            id="merge-progress",
                            value=0,
                            striped=True,
                            animated=True,
                            className="mb-2"
                        ),
                        html.Div(id="merge-status")
                    ], id="merge-progress-container", style={"display": "none"})
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="merge-cancel-btn", color="secondary", className="me-2"),
                    dbc.Button([
                        html.I(className="fas fa-layer-group me-2"),
                        "Confirmar y Unir"
                    ], id="merge-confirm-btn", color="success", disabled=True)
                ])
            ], id="merge-datasets-modal", is_open=False, size="lg"),
            
            # Store para datos de selección múltiple
            dcc.Store(id="multi-select-data", data={"active": False, "selected": []})
            
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
                                    html.Label("Archivo de clases para entrenamiento:", className="fw-bold mb-2"),
                                    dbc.Select(
                                        id="classes-source-selector",
                                        options=self._get_classes_options(),
                                        value="default",
                                        className="mb-3"
                                    ),
                                    dbc.Button([
                                        html.I(className="fas fa-sync me-2"),
                                        "Actualizar Lista"
                                    ], id="refresh-training-classes-btn", color="info", outline=True, size="sm")
                                ], md=6),
                                dbc.Col([
                                    html.Label("Información del archivo seleccionado:", className="fw-bold mb-2"),
                                    html.Div(id="training-classes-file-info", children=[
                                        dbc.Alert([
                                            html.I(className="fas fa-file-alt me-2"),
                                            "Usando archivo data.yaml por defecto"
                                        ], color="info")
                                    ], className="mb-3")
                                ], md=6)
                            ]),
                            
                            # Resumen de clases seleccionadas
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Resumen de clases para entrenamiento:", className="fw-bold mb-2"),
                                    html.Div(id="training-classes-summary", children=[
                                        dbc.Alert([
                                            html.I(className="fas fa-tags me-2"),
                                            "Las clases se cargarán según el archivo seleccionado"
                                        ], color="secondary")
                                    ], className="mt-3")
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
             Input('processing-status', 'data'),
             Input('multi-select-data', 'data')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def load_videos(refresh_clicks, videos_folder, processing_status, multi_select_data, current_page):
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
                grid = self._create_videos_grid(expanded_videos, processing_status, multi_select_data)
                
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
                
                # Expandir videos para incluir subdatasets de AutoDistill y datasets unidos
                expanded_videos = self._expand_videos_with_subdatasets(videos)
                
                return [expanded_videos]
                
            except Exception as e:
                print(f"Error cargando videos iniciales: {e}")
                return [[]]
        
        # Callback para actualizar componentes visuales cuando cambia videos-data
        @self.app.callback(
            [Output('videos-stats', 'children', allow_duplicate=True),
             Output('videos-grid', 'children', allow_duplicate=True)],
            [Input('videos-data', 'data')],
            [State('current-page', 'data'),
             State('processing-status', 'data'),
             State('multi-select-data', 'data')],
            prevent_initial_call=True
        )
        def update_videos_display(videos_data, current_page, processing_status, multi_select_data):
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
                grid = self._create_videos_grid(videos_data, processing_status or {}, multi_select_data)
                
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
             State('current-page', 'data'),
             State({'type': 'classes-selector', 'index': ALL}, 'value'),
             State({'type': 'classes-selector', 'index': ALL}, 'id')],
            prevent_initial_call=True
        )
        def open_annotation_tool_for_video(review_clicks, videos_data, current_page, classes_values, classes_ids):
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
                
                # Buscar las clases seleccionadas para este video específico
                selected_classes_file = None
                if classes_values and classes_ids:
                    for value, cls_id in zip(classes_values, classes_ids):
                        if cls_id['index'] == video_idx and value and value != "default":
                            selected_classes_file = value
                            break
                
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
                    
                    # Primero recargar imágenes y configuración para el nuevo dataset
                    self._reload_dataset_for_folder(frames_folder)
                    
                    # DESPUÉS cargar clases personalizadas si se especifica un archivo
                    # Esto es importante porque así las clases personalizadas sobrescriben las por defecto
                    if selected_classes_file:
                        self._load_custom_classes(selected_classes_file)
                    
                    # Verificar que hay imágenes
                    if not self.image_files:
                        print(f"❌ Error: No se encontraron imágenes en {frames_folder}")
                        return no_update, no_update
                    
                    print(f"✅ Dataset cargado exitosamente: {len(self.image_files)} imágenes")
                    
                    # Si se cargaron clases personalizadas, regenerar la página de anotación para reflejar los cambios
                    annotation_page = self.create_annotation_page()
                    
                    return annotation_page, {'page': 'annotation'}
                        
            except Exception as e:
                print(f"Error abriendo herramienta para video: {e}")
                return no_update, no_update
            
            return no_update, no_update

        # Callback para manejar selección de archivos de clases en videos
        @self.app.callback(
            [Output('files-toast', 'is_open', allow_duplicate=True),
             Output('files-toast', 'children', allow_duplicate=True)],
            [Input({'type': 'classes-selector', 'index': ALL}, 'value')],
            [State({'type': 'classes-selector', 'index': ALL}, 'id')],
            prevent_initial_call=True
        )
        def handle_video_classes_selection(values, ids):
            """Manejar selección de archivos de clases para videos"""
            from pathlib import Path
            import json
            import re
            
            ctx = callback_context
            if not ctx.triggered:
                return no_update, no_update
            
            try:
                # Encontrar qué selector cambió
                triggered_prop = ctx.triggered[0]['prop_id']
                if 'classes-selector' in triggered_prop:
                    # Extraer el valor e índice del selector que cambió
                    match = re.search(r'"index":(\d+)', triggered_prop)
                    if match:
                        video_index = match.group(1)
                        
                        # Obtener el valor seleccionado
                        for i, (value, selector_id) in enumerate(zip(values, ids)):
                            if str(selector_id['index']) == video_index and value and value != "default":
                                # Cargar información del archivo de clases
                                classes_dir = Path('classes')
                                file_path = classes_dir / value
                                
                                if file_path.exists():
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    
                                    message = dbc.Alert([
                                        html.Strong(f"✅ Archivo de clases asignado al video: "),
                                        html.Br(),
                                        html.Span(f"📁 {data.get('name', 'Sin nombre')} ({len(data.get('classes', []))} clases)")
                                    ], color="success")
                                    
                                    return True, message
                
                return no_update, no_update
                
            except Exception as e:
                error_message = dbc.Alert(f"❌ Error: {str(e)}", color="danger")
                return True, error_message

        # Callback clientside para abrir explorador de archivos cuando se hace clic en "Agregar Videos"
        self.app.clientside_callback(
            """
            function(n_clicks) {
                if (n_clicks) {
                    setTimeout(function() {
                        var uploadElement = document.getElementById('video-upload').getElementsByTagName('input')[0];
                        if (uploadElement) {
                            uploadElement.click();
                        }
                    }, 100);
                }
                return "";
            }
            """,
            Output('video-upload', 'style'),
            [Input('add-videos-btn', 'n_clicks')],
            prevent_initial_call=True
        )

        # Callback para procesar videos subidos
        @self.app.callback(
            [Output('files-toast', 'is_open', allow_duplicate=True),
             Output('files-toast', 'children', allow_duplicate=True),
             Output('videos-data', 'data', allow_duplicate=True)],
            [Input('video-upload', 'contents')],
            [State('video-upload', 'filename'),
             State('videos-folder-path', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def process_uploaded_videos(contents, filenames, videos_folder, current_page):
            """Procesar videos subidos y moverlos a la carpeta de videos"""
            # Solo ejecutar si estamos en la página de archivos
            if not current_page or current_page.get('page') != 'files':
                return no_update, no_update, no_update
                
            if not contents or not filenames:
                return no_update, no_update, no_update
            
            try:
                import base64
                
                # Asegurar que la carpeta de videos existe
                videos_folder = videos_folder or "videos"
                os.makedirs(videos_folder, exist_ok=True)
                
                successful_moves = []
                failed_moves = []
                
                # Procesar cada archivo
                if not isinstance(contents, list):
                    contents = [contents]
                    filenames = [filenames]
                
                for content, filename in zip(contents, filenames):
                    try:
                        # Decodificar el contenido base64
                        content_type, content_string = content.split(',')
                        decoded = base64.b64decode(content_string)
                        
                        # Crear la ruta de destino
                        dest_path = os.path.join(videos_folder, filename)
                        
                        # Evitar sobrescribir archivos existentes
                        counter = 1
                        original_dest = dest_path
                        while os.path.exists(dest_path):
                            name, ext = os.path.splitext(original_dest)
                            dest_path = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        # Guardar el archivo
                        with open(dest_path, 'wb') as f:
                            f.write(decoded)
                        
                        successful_moves.append(filename)
                        print(f"✅ Video guardado: {dest_path}")
                        
                    except Exception as e:
                        failed_moves.append(f"{filename}: {str(e)}")
                        print(f"❌ Error guardando {filename}: {e}")
                
                # Preparar mensaje de notificación
                if successful_moves:
                    success_msg = f"✅ {len(successful_moves)} video(s) agregado(s) exitosamente"
                    if failed_moves:
                        success_msg += f"\n❌ {len(failed_moves)} falló(s)"
                    
                    # Recargar lista de videos
                    from utils.video_processor import VideoProcessor
                    processor = VideoProcessor(videos_folder)
                    updated_videos = processor.get_video_files()
                    
                    return True, success_msg, updated_videos
                else:
                    error_msg = f"❌ No se pudo agregar ningún video"
                    if failed_moves:
                        error_msg += f"\nErrores: {'; '.join(failed_moves[:3])}"
                    
                    return True, error_msg, no_update
                    
            except Exception as e:
                error_msg = f"❌ Error procesando videos: {str(e)}"
                print(f"Error en process_uploaded_videos: {e}")
                return True, error_msg, no_update

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
            """Cargar datasets disponibles desde las carpetas output y Merged"""
            if not current_page or current_page.get('page') != 'autodistill':
                return no_update
            
            try:
                options = []
                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                
                # Buscar en carpeta output (datasets de videos procesados)
                output_path = Path('output')
                if output_path.exists():
                    for folder in output_path.iterdir():
                        if folder.is_dir():
                            # Verificar que la carpeta contiene imágenes
                            has_images = any(
                                any(folder.glob(f'*{ext}')) for ext in image_extensions
                            )
                            
                            if has_images:
                                # Contar imágenes
                                image_count = sum(
                                    len(list(folder.glob(f'*{ext}'))) for ext in image_extensions
                                )
                                
                                options.append({
                                    'label': f"📹 {folder.name} ({image_count} imágenes)",
                                    'value': str(folder)
                                })
                
                # Buscar en carpeta Merged (datasets unidos)
                merged_path = Path('Merged')
                if merged_path.exists():
                    for folder in merged_path.iterdir():
                        if folder.is_dir():
                            # Verificar que la carpeta contiene imágenes
                            has_images = any(
                                any(folder.glob(f'*{ext}')) for ext in image_extensions
                            )
                            
                            if has_images:
                                # Contar imágenes
                                image_count = sum(
                                    len(list(folder.glob(f'*{ext}'))) for ext in image_extensions
                                )
                                
                                options.append({
                                    'label': f"🔗 {folder.name} ({image_count} imágenes) - Dataset Unido",
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
                       "", False, True, True)  # Botón inicio habilitado, stop deshabilitado
            # Botón start presionado
            if triggered_id == 'autodistill-start-btn' and start_clicks:
                # Validar entradas
                if not dataset_path:
                    return (0, "Error", 
                           dbc.Alert("❌ Por favor selecciona un dataset", color="danger"),
                           "", True, False, True)  # Botón inicio deshabilitado, stop habilitado
                if not ontology_text.strip():
                    return (0, "Error", 
                           dbc.Alert("❌ Por favor define las clases en la ontología", color="danger"),
                           "", True, False, True)  # Botón inicio deshabilitado, stop habilitado
                try:
                    # Parsear ontología (formato simple: una clase por línea)
                    classes = [line.strip() for line in ontology_text.strip().split('\n') 
                              if line.strip()]
                    if not classes:
                        return (0, "Error", 
                               dbc.Alert("❌ No se encontraron clases válidas en la ontología", color="danger"),
                               "", True, False, True)  # Botón inicio deshabilitado, stop habilitado
                    # Ejecutar AutoDistill real
                    iou_threshold = 0.5  # Valor por defecto
                    result = self._run_autodistill_process(
                        dataset_path, base_model, classes, 
                        confidence_threshold, iou_threshold
                    )
                    # Forzar deshabilitado del botón de inicio
                    if isinstance(result, tuple) and len(result) == 7:
                        # autodistill-start-btn disabled, autodistill-stop-btn enabled
                        return (*result[:-3], True, False, *result[-1:])
                    return result
                except Exception as e:
                    error_msg = f"Error procesando: {str(e)}"
                    return (0, "Error", 
                           dbc.Alert(f"❌ {error_msg}", color="danger"),
                           "", True, False, True)  # Botón inicio deshabilitado, stop habilitado
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
             State('new-classes-list', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def save_classes_file(save_clicks, filename, description, classes_text, current_page):
            """Guardar nuevo archivo de clases"""
            # Verificar que estamos en la página correcta
            if not current_page or current_page.get('page') != 'classes':
                return no_update, no_update, no_update, no_update, no_update
                
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
        
        # Callback para actualizar lista después de guardar
        @self.app.callback(
            Output('classes-files-list', 'children', allow_duplicate=True),
            [Input('refresh-classes-list', 'n_clicks')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def refresh_classes_list_after_save(refresh_clicks, current_page):
            """Actualizar lista cuando se hace refresh"""
            if not current_page or current_page.get('page') != 'classes':
                return no_update
                
            try:
                classes_files = list(classes_dir.glob("*.json"))
                
                if not classes_files:
                    return [dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        "No hay archivos de clases creados aún. Crea tu primer archivo usando el panel de arriba."
                    ], color="info", className="mb-3")]
                
                file_cards = []
                for file_path in sorted(classes_files):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        card = dbc.Card([
                            dbc.CardBody([
                                html.H5([
                                    html.I(className="fas fa-file-alt me-2"),
                                    data.get('name', file_path.stem)
                                ], className="card-title"),
                                html.P(data.get('description', 'Sin descripción'), 
                                      className="text-muted mb-2"),
                                html.Small([
                                    html.I(className="fas fa-tags me-1"),
                                    f"{data.get('count', 0)} clases"
                                ], className="text-muted"),
                                html.Br(),
                                html.Small([
                                    html.I(className="fas fa-clock me-1"),
                                    f"Creado: {data.get('created_at', 'Desconocido')[:10]}"
                                ], className="text-muted"),
                                dbc.ButtonGroup([
                                    dbc.Button([
                                        html.I(className="fas fa-eye me-1"),
                                        "Ver"
                                    ], size="sm", color="outline-primary"),
                                    dbc.Button([
                                        html.I(className="fas fa-edit me-1"),
                                        "Editar"
                                    ], size="sm", color="outline-secondary"),
                                    dbc.Button([
                                        html.I(className="fas fa-trash me-1"),
                                        "Eliminar"
                                    ], size="sm", color="outline-danger")
                                ], className="mt-3")
                            ])
                        ], className="mb-3 shadow-sm")
                        
                        file_cards.append(card)
                    except Exception as e:
                        print(f"Error cargando {file_path}: {e}")
                        continue
                
                return file_cards
            except Exception as e:
                return [dbc.Alert(f"❌ Error cargando archivos: {str(e)}", color="danger")]
            
            return no_update
        
        # Callback para cargar lista de archivos de clases
        @self.app.callback(
            Output('classes-files-list', 'children'),
            [Input('current-page', 'data'),
             Input('refresh-classes-list', 'n_clicks')],
            prevent_initial_call=False
        )
        def load_classes_files_list(current_page, refresh_clicks):
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

        # Callback específico para actualizar el selector de entrenamiento
        @self.app.callback(
            Output('custom-classes-file-selector', 'options'),
            [Input('current-page', 'data'),
             Input('refresh-classes-files-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def update_training_classes_selector(current_page, refresh_clicks):
            """Actualizar selector de entrenamiento específicamente"""
            try:
                # Solo actualizar si estamos en la página de entrenamiento
                if not current_page or current_page.get('page') != 'training':
                    return no_update
                
                print(f"🏋️ Actualizando selector de entrenamiento...")
                    
                # Cargar archivos de clases disponibles
                classes_files = list(classes_dir.glob("*.json"))
                print(f"📁 Archivos de clases encontrados: {[f.name for f in classes_files]}")
                
                # Opciones base
                base_options = [{"label": "Usar data.yaml por defecto", "value": "default"}]
                
                # Agregar archivos de clases
                for file_path in sorted(classes_files):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        base_options.append({
                            "label": f"📁 {data.get('name', file_path.stem)} ({len(data.get('classes', []))} clases)",
                            "value": file_path.name
                        })
                    except Exception as e:
                        print(f"Error cargando {file_path}: {e}")
                        continue
                
                return base_options
                
            except Exception as e:
                print(f"Error actualizando selector de entrenamiento: {e}")
                return [{"label": "Usar data.yaml por defecto", "value": "default"}]

        # Callback para actualizar el selector principal de clases en entrenamiento
        @self.app.callback(
            Output('classes-source-selector', 'options'),
            [Input('current-page', 'data'),
             Input('refresh-training-classes-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def update_main_training_classes_selector(current_page, refresh_clicks):
            """Actualizar selector principal de clases en entrenamiento"""
            try:
                # Solo actualizar si estamos en la página de entrenamiento
                if not current_page or current_page.get('page') != 'training':
                    return no_update
                
                print(f"🏋️ Actualizando selector principal de entrenamiento...")
                
                # Usar la función helper para obtener las opciones
                return self._get_classes_options()
                
            except Exception as e:
                print(f"Error actualizando selector principal de entrenamiento: {e}")
                return [{"label": "Usar data.yaml por defecto", "value": "default"}]

        # Callback específico para actualizar los selectores de la página de archivos
        @self.app.callback(
            Output({'type': 'classes-selector', 'index': ALL}, 'options'),
            [Input('current-page', 'data'),
             Input('files-grid-data', 'data')],
            prevent_initial_call=True
        )
        def update_files_classes_selectors(current_page, files_data):
            """Actualizar selectores de archivos específicamente"""
            try:
                # Solo actualizar si estamos en la página de archivos
                if not current_page or current_page.get('page') != 'files':
                    return no_update
                
                print(f"🔄 Actualizando selectores de archivos...")
                
                # Cargar archivos de clases disponibles
                classes_files = list(classes_dir.glob("*.json"))
                print(f"📁 Archivos de clases encontrados: {[f.name for f in classes_files]}")
                
                # Opciones base
                base_options = [{"label": "Usar data.yaml por defecto", "value": "default"}]
                
                # Agregar archivos de clases
                for file_path in sorted(classes_files):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        base_options.append({
                            "label": f"📁 {data.get('name', file_path.stem)} ({len(data.get('classes', []))} clases)",
                            "value": file_path.name
                        })
                    except Exception as e:
                        print(f"Error cargando {file_path}: {e}")
                        continue
                
                # Obtener número de videos/datasets actual
                try:
                    videos_data = self._get_videos_data()
                    num_videos = len(videos_data)
                    print(f"📊 Número de videos detectado: {num_videos}")
                except:
                    num_videos = 20  # Fallback
                
                # Retornar las opciones para el número correcto de selectores
                return [base_options] * num_videos
                
            except Exception as e:
                print(f"Error actualizando selectores de archivos: {e}")
                # Retornar lista vacía en caso de error
                try:
                    videos_data = self._get_videos_data()
                    num_videos = len(videos_data)
                except:
                    num_videos = 20
                return [base_options] * num_videos

        # Callback para mostrar información del archivo de clases seleccionado en entrenamiento
        @self.app.callback(
            Output('selected-classes-file-info', 'children'),
            [Input('custom-classes-file-selector', 'value')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def show_selected_classes_info(selected_file, current_page):
            """Mostrar información del archivo de clases seleccionado"""
            # Solo procesar si estamos en la página de entrenamiento
            if not current_page or current_page.get('page') != 'training':
                return no_update
                
            if not selected_file or selected_file == "default":
                return html.Div([
                    html.Small("Se usará el archivo data.yaml del dataset", className="text-muted")
                ])
            
            try:
                file_path = classes_dir / selected_file
                if not file_path.exists():
                    return dbc.Alert("❌ Archivo no encontrado", color="danger")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                classes_preview = ", ".join(data.get('classes', [])[:8])
                if len(data.get('classes', [])) > 8:
                    classes_preview += "..."
                
                return dbc.Card([
                    dbc.CardBody([
                        html.H6(data.get('name', 'Sin nombre'), className="card-title small"),
                        html.P(data.get('description', 'Sin descripción'), className="card-text small text-muted"),
                        html.Div([
                            html.Strong(f"{len(data.get('classes', []))} clases: ", className="small"),
                            html.Span(classes_preview, className="small text-info")
                        ])
                    ], className="py-2")
                ], className="border-light")
                
            except Exception as e:
                return dbc.Alert(f"❌ Error: {str(e)}", color="danger")

        # Callback para actualizar información del archivo de clases seleccionado en entrenamiento
        @self.app.callback(
            [Output('training-classes-file-info', 'children'),
             Output('training-classes-summary', 'children', allow_duplicate=True)],
            [Input('classes-source-selector', 'value'),
             Input('refresh-training-classes-btn', 'n_clicks')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def update_training_classes_info(selected_file, refresh_clicks, current_page):
            """Actualizar información del archivo de clases seleccionado"""
            # Solo procesar si estamos en la página de entrenamiento
            if not current_page or current_page.get('page') != 'training':
                return no_update, no_update
                
            try:
                if selected_file == "default" or not selected_file:
                    # Usar data.yaml por defecto
                    info_content = dbc.Alert([
                        html.I(className="fas fa-file-alt me-2"),
                        "Usando archivo data.yaml por defecto"
                    ], color="info")
                    
                    summary_content = dbc.Alert([
                        html.I(className="fas fa-tags me-2"),
                        "Se usarán las clases definidas en el archivo data.yaml del dataset seleccionado"
                    ], color="primary")
                    
                    return info_content, summary_content
                
                else:
                    # Cargar información del archivo seleccionado
                    from pathlib import Path
                    import json
                    
                    classes_dir = Path('classes')
                    file_path = classes_dir / selected_file
                    
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        classes = data.get('classes', [])
                        
                        info_content = dbc.Alert([
                            html.H6([
                                html.I(className="fas fa-file me-2"),
                                data.get('name', 'Sin nombre')
                            ], className="mb-2"),
                            html.P(data.get('description', 'Sin descripción'), className="mb-2"),
                            html.Small([
                                html.I(className="fas fa-calendar me-1"),
                                f"Creado: {data.get('created_at', 'Desconocido')[:10]}"
                            ], className="text-muted")
                        ], color="success")
                        
                        summary_content = dbc.Alert([
                            html.H6([
                                html.I(className="fas fa-tags me-2"),
                                f"Clases para entrenamiento ({len(classes)})"
                            ], className="mb-2"),
                            html.P(", ".join(classes[:15]) + ("..." if len(classes) > 15 else ""))
                        ], color="success")
                        
                        return info_content, summary_content
                    
                    else:
                        error_content = dbc.Alert([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"No se pudo encontrar el archivo: {selected_file}"
                        ], color="danger")
                        
                        return error_content, error_content
                    
            except Exception as e:
                error_content = dbc.Alert(f"❌ Error: {str(e)}", color="danger")
                return error_content, error_content

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
                options = []
                
                # 1. Buscar en carpeta 'output' (datasets procesados)
                output_path = Path('output')
                if output_path.exists():
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
                
                # 2. Buscar datasets unidos en 'Merged'
                merged_path = Path('Merged')
                if merged_path.exists():
                    for dataset_folder in merged_path.iterdir():
                        if dataset_folder.is_dir():
                            # Filtrar carpetas que no son datasets válidos
                            if dataset_folder.name in ['labels', '__pycache__', '.git', 'runs', 'weights']:
                                continue
                            
                            # Verificar si tiene imágenes
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            image_count = 0
                            label_count = 0
                            
                            for ext in image_extensions:
                                images = list(dataset_folder.glob(f'*{ext}'))
                                image_count += len(images)
                            
                            # Verificar si tiene etiquetas (en la carpeta principal o en subcarpeta labels)
                            labels = list(dataset_folder.glob('*.txt'))
                            labels_subfolder = dataset_folder / 'labels'
                            if labels_subfolder.exists():
                                labels.extend(list(labels_subfolder.glob('*.txt')))
                            label_count = len(labels)
                            
                            has_images = image_count > 0
                            has_labels = label_count > 0
                            
                            # Solo agregar datasets que tengan al menos imágenes
                            if has_images:
                                if has_labels:
                                    # Marcar datasets unidos con un icono especial
                                    icon = "🔗" if dataset_folder.name.startswith('merged_') else "📁"
                                    options.append({
                                        'label': f"{icon} {dataset_folder.name} ({image_count} imágenes, {label_count} etiquetas)",
                                        'value': str(dataset_folder)
                                    })
                                else:
                                    # Dataset sin etiquetas pero con imágenes (para AutoDistill)
                                    icon = "🔗" if dataset_folder.name.startswith('merged_') else "📷"
                                    options.append({
                                        'label': f"{icon} {dataset_folder.name} ({image_count} imágenes, sin etiquetas)",
                                        'value': str(dataset_folder)
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
             State('classes-source-selector', 'value'),
             State('training-epochs', 'value'),
             State('training-batch-size', 'value'),
             State('training-lr', 'value'),
             State('training-img-size', 'value'),
             State('training-patience', 'value'),
             State('current-page', 'data')],
            prevent_initial_call=True
        )
        def start_training(start_clicks, stop_clicks, dataset_path, classes_source, epochs, batch_size, 
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
                return False, toast_message, False, True, 0, "Detenido", "", ""  # Botón inicio habilitado, stop deshabilitado
            # Botón start presionado
            if triggered_id == 'training-start-btn' and start_clicks:
                if not dataset_path:
                    toast_message = dbc.Alert("❌ Por favor selecciona un dataset", color="danger")
                    return True, toast_message, False, True, 0, "Error", "", ""
                try:
                    # Cargar clases personalizadas si se especificó un archivo
                    if classes_source and classes_source != "default":
                        print(f"🏷️ Cargando clases personalizadas desde: {classes_source}")
                        self._load_custom_classes(classes_source)
                    else:
                        print(f"🏷️ Usando clases por defecto del data.yaml")
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
                    # Deshabilitar botón de inicio mientras entrena
                    result = self._start_real_training(
                        dataset_path, epochs, batch_size, learning_rate, 
                        image_size, patience, len(train_images), len(train_labels)
                    )
                    # Forzar deshabilitado del botón de inicio
                    if isinstance(result, tuple) and len(result) == 8:
                        # training-start-btn disabled, training-stop-btn enabled
                        return (*result[:-2], True, False)
                    return result
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
            
            # Convertir clases de diccionario a lista para YOLO
            classes_list = list(self.classes.values())
            
            data_config = {
                'train': train_images_path,
                'val': valid_images_path, 
                'nc': len(classes_list),  # número de clases
                'names': classes_list    # lista de nombres de clases
            }
            
            # Verificar que las carpetas existan
            if not os.path.exists(train_images_path):
                error_msg = f"No existe la carpeta de entrenamiento: {train_images_path}"
                print(f"❌ Error: {error_msg}")
                toast_message = dbc.Alert(f"❌ {error_msg}", color="danger")
                return True, toast_message, False, True, 0, "Error", "", ""
            if not os.path.exists(valid_images_path):
                error_msg = f"No existe la carpeta de validación: {valid_images_path}"
                print(f"❌ Error: {error_msg}")
                toast_message = dbc.Alert(f"❌ {error_msg}", color="danger")
                return True, toast_message, False, True, 0, "Error", "", ""
            
            # Guardar configuración
            with open(data_yaml_path, 'w') as f:
                yaml.dump(data_config, f)
            
            print(f"🚀 Iniciando entrenamiento con YOLOv8...")
            print(f"📁 Dataset: {dataset_path}")
            print(f"🖼️ Imágenes de entrenamiento: {train_images_path}")
            print(f"🖼️ Imágenes de validación: {valid_images_path}")
            print(f"🏷️ Clases: {classes_list}")
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
                if max_class_idx >= len(classes_list):
                    error_msg = f"Se encontraron clases con índice {max_class_idx} pero solo hay {len(classes_list)} clases definidas"
                    print(f"❌ Error: {error_msg}")
                    print(f"   Clases válidas: {list(range(len(classes_list)))}")
                    print(f"   Nombres de clases: {classes_list}")
                    toast_message = dbc.Alert(f"❌ {error_msg}", color="danger")
                    return True, toast_message, False, True, 0, "Error", "", ""
                else:
                    print(f"✅ Etiquetas validadas correctamente")
                    print(f"   - Índice máximo de clase encontrado: {max_class_idx}")
                    print(f"   - Número de clases definidas: {len(classes_list)}")
                    print(f"   - Clases: {classes_list}")
            else:
                error_msg = "No se encontraron etiquetas válidas en el dataset"
                print(f"⚠️ {error_msg}")
                toast_message = dbc.Alert(f"⚠️ {error_msg}", color="warning")
                return True, toast_message, False, True, 0, "Error", "", ""
            
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

    def _create_videos_grid(self, videos, processing_status=None, multi_select_data=None):
        """Crear grid de tarjetas de video"""
        from pathlib import Path
        
        if not videos:
            return []
        
        processing_status = processing_status or {}
        multi_select_data = multi_select_data or {"active": False, "selected": []}
        
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
                    dataset_type = video.get('dataset_type', 'unknown')
                    print(f"🔍 Dataset {video['name']}: is_subdataset={is_subdataset}, dataset_type={dataset_type}, has_labels={video.get('has_labels', False)}")
                    
                    if video.get('has_labels', False) and dataset_type == 'autodistill':
                        # Subdataset con etiquetas de AutoDistill
                        label_count = video.get('label_count', 0)
                        action_buttons = dbc.Button([
                            html.I(className="fas fa-robot me-2"),
                            "Abrir Dataset AI"
                        ], id={'type': 'review-btn', 'index': idx}, 
                         color="info", size="sm", className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-robot me-1"),
                            f"AutoDistill - {video.get('subdataset_type', 'Dataset').title()}"
                        ], color="info", className="mb-2")
                    elif dataset_type == 'merged':
                        # Dataset unido - tratar como dataset completo
                        print(f"🔗 Creando botones para dataset unido: {video['name']}")
                        action_buttons = dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-tags me-2"),
                                "Revisar Etiquetas"
                            ], id={'type': 'review-btn', 'index': idx}, 
                             color="primary", size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-robot me-2"),
                                "AutoDistill"
                            ], id={'type': 'autodistill-btn', 'index': idx}, 
                             color="success", size="sm")
                        ], className="w-100")
                        
                        status_badge = dbc.Badge([
                            html.I(className="fas fa-layer-group me-1"),
                            f"Dataset Unido - {video.get('label_count', 0)} etiquetas"
                        ], color="warning", className="mb-2")
                    else:
                        # Subdataset solo con imágenes
                        print(f"⚠️ Dataset {video['name']} clasificado como 'solo imágenes': dataset_type={dataset_type}")
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
                    # Verificar si tiene etiquetas de AutoDistill usando la información del video
                    has_autodistill_labels = (video.get('has_autodistill_labels', False) or 
                                            video.get('dataset_type') == 'autodistill')
                    
                    if not has_autodistill_labels:
                        # Verificación adicional por si no se detectó antes
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
            
            # Crear contenido de la tarjeta
            card_body_content = [
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
                        options=self._get_classes_options(),
                        value="default",
                        size="sm",
                        className="mb-2"
                    )
                ], className="mb-3"),
                
                # Botones de acción
                action_buttons
            ]
            
            # Agregar checkbox si está en modo selección múltiple
            card_children = []
            if multi_select_data.get("active", False):
                is_selected = idx in multi_select_data.get("selected", [])
                card_children.append(
                    dbc.Checkbox(
                        id={'type': 'dataset-checkbox', 'index': idx},
                        value=is_selected,
                        className="position-absolute",
                        style={"top": "10px", "right": "10px", "z-index": 10}
                    )
                )
            
            card_children.append(dbc.CardBody(card_body_content, className="p-3"))
            
            # Crear tarjeta
            card = dbc.Col([
                dbc.Card(card_children, className="h-100 border-0 shadow-sm hover-card",
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
            # Verificar si el video tiene etiquetas de AutoDistill
            video_copy = video.copy()
            if self._has_autodistill_labels(video):
                video_copy['has_autodistill_labels'] = True
                video_copy['dataset_type'] = 'autodistill'
            
            # Agregar el video original (posiblemente modificado)
            expanded_videos.append(video_copy)
            
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
                                'duration_str': f"{image_count} imágenes",
                                'frame_count': image_count,
                                'existing_frames': image_count,
                                'file_size_str': video.get('file_size_str', 'AutoDistill'),
                                'resolution': video.get('resolution', 'Original'),
                                'has_frames': has_images,
                                'has_labels': has_labels,
                                'label_count': label_count,
                                'is_subdataset': True,
                                'parent_video': video['name_without_ext'],
                                'dataset_type': 'autodistill',  # Marcar como AutoDistill
                                'subdataset_type': subdir  # Mantener info de si es train/valid
                            }
                            expanded_videos.append(subdataset)
        
        # Buscar datasets unidos en Merged
        merged_path = Path('Merged')
        if merged_path.exists():
            for dataset_folder in merged_path.iterdir():
                if dataset_folder.is_dir():
                    # Filtrar carpetas que no son datasets válidos
                    if dataset_folder.name in ['labels', '__pycache__', '.git', 'runs', 'weights']:
                        continue
                        
                    # Verificar si tiene imágenes
                    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                    image_count = 0
                    label_count = 0
                    
                    for ext in image_extensions:
                        images = list(dataset_folder.glob(f'*{ext}'))
                        image_count += len(images)
                    
                    # Verificar si tiene etiquetas (en la carpeta principal o en subcarpeta labels)
                    labels = list(dataset_folder.glob('*.txt'))
                    labels_subfolder = dataset_folder / 'labels'
                    if labels_subfolder.exists():
                        labels.extend(list(labels_subfolder.glob('*.txt')))
                    label_count = len(labels)
                    
                    print(f"🏷️ Dataset {dataset_folder.name}: {image_count} imágenes, {label_count} etiquetas")
                    if labels_subfolder.exists():
                        print(f"🏷️ Etiquetas en subcarpeta: {len(list(labels_subfolder.glob('*.txt')))}")
                    
                    has_images = image_count > 0
                    has_labels = label_count > 0
                    
                    # Solo agregar datasets que tengan al menos imágenes
                    if has_images:
                        # Crear entrada para el dataset unido
                        merged_dataset = {
                            'name': dataset_folder.name,
                            'name_without_ext': dataset_folder.name,
                            'path': str(dataset_folder),
                            'images_path': str(dataset_folder),
                            'labels_path': str(dataset_folder) if has_labels else None,
                            'size': 'N/A',
                            'duration': f"{image_count} imágenes, {label_count} etiquetas",
                            'duration_str': f"{image_count} imágenes",
                            'frame_count': image_count,
                            'existing_frames': image_count,
                            'file_size_str': 'N/A',
                            'resolution': 'Múltiples',
                            'has_frames': has_images,
                            'has_labels': has_labels,
                            'label_count': label_count,
                            'is_subdataset': True,
                            'parent_video': 'merged_dataset',
                            'dataset_type': 'merged'
                        }
                        expanded_videos.append(merged_dataset)
        
        return expanded_videos
    
    def _get_videos_data(self):
        """Obtener datos de todos los videos y subdatasets"""
        try:
            from utils.video_processor import VideoProcessor
            processor = VideoProcessor("videos")  # Usar directorio por defecto
            videos = processor.get_video_files()
            
            # Expandir videos para incluir subdatasets de AutoDistill
            expanded_videos = self._expand_videos_with_subdatasets(videos)
            
            return expanded_videos
        except Exception as e:
            print(f"Error obteniendo datos de videos: {e}")
            return []

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

    def _load_custom_classes(self, classes_file):
        """Cargar clases personalizadas desde un archivo JSON"""
        try:
            from pathlib import Path
            import json
            
            classes_path = Path('classes') / classes_file
            if classes_path.exists():
                with open(classes_path, 'r', encoding='utf-8') as f:
                    classes_data = json.load(f)
                
                # Actualizar las clases disponibles
                custom_classes = classes_data.get('classes', [])
                self.config_loader.classes = {i: class_name for i, class_name in enumerate(custom_classes)}
                self.config_loader.classes_list = custom_classes
                
                # Actualizar las clases globales de la instancia
                self.classes = self.config_loader.classes
                
                print(f"🔧 self.classes actualizado: {self.classes}")
                print(f"🔧 Tipo de self.classes: {type(self.classes)}")
                
                # Actualizar los colores para las nuevas clases
                self.class_colors = self.config_loader.get_colors(len(custom_classes))
                
                print(f"✅ Clases personalizadas cargadas desde {classes_file}: {custom_classes}")
                print(f"🔧 Config_loader.classes actualizado: {self.config_loader.classes}")
                print(f"🔧 Config_loader.classes_list actualizado: {self.config_loader.classes_list}")
                
                # Actualizar el annotation_manager
                if hasattr(self, 'annotation_manager'):
                    if hasattr(self.annotation_manager, 'config'):
                        self.annotation_manager.config.classes = self.config_loader.classes
                    elif hasattr(self.annotation_manager, 'classes'):
                        self.annotation_manager.classes = self.config_loader.classes
                
                # Actualizar el figure_generator con las nuevas clases y colores
                if hasattr(self, 'figure_generator'):
                    self.figure_generator.class_colors = self.class_colors
                    print(f"🎨 Figure generator actualizado con {len(self.class_colors)} colores")
                
                # Actualizar el callback_manager
                if hasattr(self, 'callback_manager'):
                    self.callback_manager.classes = self.classes
                    print(f"🔄 Callback manager actualizado con clases: {list(self.classes.values())}")
                    
            else:
                print(f"❌ Archivo de clases no encontrado: {classes_path}")
                
        except Exception as e:
            print(f"Error cargando clases personalizadas: {e}")
            import traceback
            traceback.print_exc()

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

    def _setup_dataset_merge_callbacks(self):
        """Configurar callbacks para unión de datasets"""
        
        # Callback para activar/desactivar modo selección múltiple
        @self.app.callback(
            Output('multi-select-data', 'data'),
            [Input('multi-select-btn', 'n_clicks')],
            [State('multi-select-data', 'data')],
            prevent_initial_call=True
        )
        def toggle_multi_select(n_clicks, current_data):
            """Alternar modo de selección múltiple"""
            if not n_clicks:
                return no_update
                
            current_data = current_data or {"active": False, "selected": []}
            
            # Alternar estado
            new_state = not current_data.get("active", False)
            
            return {
                "active": new_state,
                "selected": [] if new_state else current_data.get("selected", [])
            }
        
        # Callback para manejar selección de checkboxes
        @self.app.callback(
            Output('multi-select-data', 'data', allow_duplicate=True),
            [Input({'type': 'dataset-checkbox', 'index': ALL}, 'value')],
            [State('multi-select-data', 'data'),
             State({'type': 'dataset-checkbox', 'index': ALL}, 'id')],
            prevent_initial_call=True
        )
        def update_selected_datasets(checkbox_values, current_data, checkbox_ids):
            """Actualizar datasets seleccionados"""
            if not checkbox_values or not checkbox_ids:
                return no_update
                
            current_data = current_data or {"active": False, "selected": []}
            selected = []
            
            for i, (value, checkbox_id) in enumerate(zip(checkbox_values, checkbox_ids)):
                if value:  # Si el checkbox está marcado
                    selected.append(checkbox_id['index'])
            
            current_data["selected"] = selected
            return current_data
        
        # Callback para actualizar texto del botón de selección múltiple
        @self.app.callback(
            Output('multi-select-btn', 'children'),
            [Input('multi-select-data', 'data')]
        )
        def update_multi_select_button_text(multi_select_data):
            """Actualizar texto del botón según el estado"""
            if not multi_select_data:
                return [html.I(className="fas fa-check-square me-2"), "Seleccionar Varios Datasets"]
                
            if multi_select_data.get("active", False):
                selected_count = len(multi_select_data.get("selected", []))
                return [
                    html.I(className="fas fa-times me-2"), 
                    f"Cancelar Selección ({selected_count} seleccionados)"
                ]
            else:
                return [html.I(className="fas fa-check-square me-2"), "Seleccionar Varios Datasets"]
        
        # Callback para habilitar/deshabilitar botón de unir datasets
        @self.app.callback(
            Output('merge-datasets-btn', 'disabled'),
            [Input('multi-select-data', 'data')]
        )
        def update_merge_button_state(multi_select_data):
            """Habilitar botón de unir solo si hay datasets seleccionados"""
            if not multi_select_data:
                return True
                
            selected_count = len(multi_select_data.get("selected", []))
            return selected_count < 2  # Necesita al menos 2 datasets para unir
        
        # Callback para abrir modal de configuración de unión
        @self.app.callback(
            Output('merge-datasets-modal', 'is_open'),
            [Input('merge-datasets-btn', 'n_clicks'),
             Input('merge-confirm-btn', 'n_clicks'),
             Input('merge-cancel-btn', 'n_clicks')],
            [State('merge-datasets-modal', 'is_open')],
            prevent_initial_call=True
        )
        def toggle_merge_modal(merge_clicks, confirm_clicks, cancel_clicks, is_open):
            """Abrir/cerrar modal de configuración"""
            ctx = callback_context
            if not ctx.triggered:
                return no_update
                
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id == 'merge-datasets-btn':
                return True
            elif button_id in ['merge-confirm-btn', 'merge-cancel-btn']:
                return False
                
            return is_open
        
        # Callback para actualizar resumen en el modal
        @self.app.callback(
            [Output('merge-summary', 'children'),
             Output('merge-confirm-btn', 'disabled')],
            [Input('merge-datasets-modal', 'is_open'),
             Input('merge-name', 'value'),
             Input('rename-strategy', 'value')],
            [State('multi-select-data', 'data')],
            prevent_initial_call=True
        )
        def update_merge_summary(modal_open, new_name, rename_strategy, multi_select_data):
            """Actualizar resumen de la operación de unión"""
            if not modal_open or not multi_select_data:
                return "", True
                
            selected_indices = multi_select_data.get("selected", [])
            if not selected_indices:
                return "No hay datasets seleccionados", True
                
            # Verificar si el botón debe estar habilitado
            button_disabled = (not new_name or not new_name.strip() or len(selected_indices) < 2)
                
            try:
                videos_data = self._get_videos_data()
                selected_datasets = [videos_data[i] for i in selected_indices if i < len(videos_data)]
                
                # Calcular total de imágenes correctamente
                from pathlib import Path
                total_images = 0
                for dataset in selected_datasets:
                    if dataset.get('is_subdataset', False):
                        # Para subdatasets, extraer el número de imágenes de duration
                        duration = dataset.get('duration', '0 imágenes')
                        try:
                            # Extraer número de imágenes de "X imágenes, Y etiquetas"
                            image_count = int(duration.split(' imágenes')[0])
                            total_images += image_count
                        except:
                            # Si no se puede extraer, intentar contar archivos directamente
                            images_path = Path(dataset.get('images_path', ''))
                            if images_path.exists():
                                image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                                for ext in image_extensions:
                                    total_images += len(list(images_path.glob(f'*{ext}')))
                    else:
                        # Para videos originales, usar existing_frames (imágenes ya extraídas)
                        total_images += dataset.get('existing_frames', 0)
                
                dataset_names = [dataset['name'] for dataset in selected_datasets]
                
                summary = [
                    html.H6("📊 Resumen de la operación:", className="text-info mb-3"),
                    html.Ul([
                        html.Li(f"Datasets a unir: {len(selected_datasets)}"),
                        html.Li(f"Total de imágenes: {total_images}"),
                        html.Li(f"Nombre del nuevo dataset: {new_name or 'Sin especificar'}"),
                        html.Li(f"Estrategia de renombrado: {'Secuencial' if rename_strategy == 'sequential' else 'Con prefijo'}")
                    ], className="text-muted"),
                    html.Hr(),
                    html.H6("📁 Datasets seleccionados:", className="text-warning mb-2"),
                    html.Ul([
                        html.Li(name, className="small") for name in dataset_names
                    ], className="text-muted small")
                ]
                
                return summary, button_disabled
                
            except Exception as e:
                return f"Error generando resumen: {str(e)}", True
        
        # Callback principal para procesar la unión de datasets
        @self.app.callback(
            [Output('merge-progress', 'value'),
             Output('merge-progress', 'children'),
             Output('merge-status', 'children'),
             Output('merge-progress-container', 'style'),
             Output('multi-select-data', 'data', allow_duplicate=True)],
            [Input('merge-confirm-btn', 'n_clicks')],
            [State('merge-name', 'value'),
             State('rename-strategy', 'value'),
             State('merge-action', 'value'),
             State('multi-select-data', 'data')],
            prevent_initial_call=True
        )
        def process_dataset_merge(confirm_clicks, new_name, rename_strategy, action, multi_select_data):
            """Procesar la unión de datasets"""
            print(f"🔄 Callback activado - confirm_clicks: {confirm_clicks}")
            print(f"🔄 new_name: {new_name}, strategy: {rename_strategy}, action: {action}")
            print(f"🔄 multi_select_data: {multi_select_data}")
            
            if not confirm_clicks or not multi_select_data:
                print("❌ Callback cancelado - sin clicks o datos")
                return no_update, no_update, no_update, no_update, no_update
                
            import shutil
            import glob
            from pathlib import Path
                
            try:
                selected_indices = multi_select_data.get("selected", [])
                if len(selected_indices) < 2:
                    return (0, "0%", 
                           dbc.Alert("❌ Necesitas seleccionar al menos 2 datasets", color="danger"),
                           {"display": "block"},
                           multi_select_data)
                
                if not new_name or not new_name.strip():
                    print("❌ Nombre del dataset vacío")
                    return (0, "0%", 
                           dbc.Alert("❌ Debes especificar un nombre para el nuevo dataset", color="danger"),
                           {"display": "block"},
                           multi_select_data)
                
                print(f"✅ Iniciando procesamiento de unión de datasets...")
                print(f"📁 Nombre del nuevo dataset: {new_name}")
                print(f"🔄 Estrategia: {rename_strategy}, Acción: {action}")
                
                # Obtener datos de los datasets seleccionados
                videos_data = self._get_videos_data()
                selected_datasets = [videos_data[i] for i in selected_indices if i < len(videos_data)]
                
                print(f"📊 Datasets seleccionados: {len(selected_datasets)}")
                
                # Crear directorio para el nuevo dataset
                base_dataset_path = "Merged"  # Usar carpeta específica para datasets unidos
                os.makedirs(base_dataset_path, exist_ok=True)  # Crear carpeta Merged si no existe
                
                new_dataset_path = os.path.join(base_dataset_path, f"merged_{new_name.strip()}")
                print(f"📁 Creando dataset en: {new_dataset_path}")
                
                # Si ya existe, agregar un número secuencial
                if os.path.exists(new_dataset_path):
                    counter = 1
                    original_path = new_dataset_path
                    while os.path.exists(new_dataset_path):
                        new_dataset_path = f"{original_path}_{counter}"
                        counter += 1
                    print(f"📁 Dataset ya existía, usando: {new_dataset_path}")
                
                os.makedirs(new_dataset_path, exist_ok=True)
                
                from pathlib import Path
                import shutil
                processed_images = 0
                
                # Función auxiliar para generar nuevo nombre
                def get_new_filename(original_name, dataset_index, image_index):
                    if rename_strategy == 'sequential':
                        return f"image_{processed_images + image_index:06d}.jpg"
                    else:  # prefix
                        dataset_name = selected_datasets[dataset_index]['name']
                        dataset_prefix = dataset_name.replace('.', '_').replace(' ', '_')
                        base_name = os.path.splitext(original_name)[0]
                        return f"{dataset_prefix}_{base_name}.jpg"
                
                # Procesar cada dataset
                for dataset_idx, dataset in enumerate(selected_datasets):
                    print(f"🔍 Dataset {dataset_idx}: {dataset['name']}")
                    print(f"🔍 Es subdataset: {dataset.get('is_subdataset', False)}")
                    print(f"🔍 Datos del dataset: {dataset}")
                    
                    if dataset.get('is_subdataset', False):
                        # Para subdatasets, usar images_path
                        images_path = Path(dataset.get('images_path', ''))
                        labels_path = Path(dataset.get('labels_path', '')) if dataset.get('labels_path') else None
                        
                        print(f"🔍 Images path: {images_path}")
                        print(f"🔍 Labels path: {labels_path}")
                        print(f"🔍 Images path existe: {images_path.exists()}")
                        
                        if images_path.exists():
                            # Obtener todas las imágenes
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            image_files = []
                            for ext in image_extensions:
                                image_files.extend(list(images_path.glob(f'*{ext}')))
                            
                            for img_idx, image_file in enumerate(image_files):
                                # Copiar/mover imagen
                                new_filename = get_new_filename(image_file.name, dataset_idx, img_idx)
                                new_img_path = os.path.join(new_dataset_path, new_filename)
                                
                                print(f"📝 DEBUG - new_dataset_path: {new_dataset_path}")
                                print(f"📝 DEBUG - new_filename: {new_filename}")
                                print(f"📝 DEBUG - new_img_path completo: {new_img_path}")
                                
                                if action == 'copy':
                                    shutil.copy2(str(image_file), new_img_path)
                                else:  # move
                                    shutil.move(str(image_file), new_img_path)
                                
                                # Copiar/mover etiquetas si existen
                                if labels_path and labels_path.exists():
                                    label_file = labels_path / (image_file.stem + '.txt')
                                    if label_file.exists():
                                        new_label_path = os.path.splitext(new_img_path)[0] + '.txt'
                                        if action == 'copy':
                                            shutil.copy2(str(label_file), new_label_path)
                                        else:  # move
                                            shutil.move(str(label_file), new_label_path)
                                
                                processed_images += 1
                    else:
                        # Para videos originales, buscar en frames_folder
                        frames_folder = dataset.get('frames_folder', '')
                        if frames_folder:
                            dataset_path = os.path.join(os.getcwd(), frames_folder)
                        else:
                            dataset_path = os.path.join(self.dataset_path, dataset['name'])
                        
                        print(f"🔍 Dataset normal path: {dataset_path}")
                        print(f"🔍 Existe dataset normal: {os.path.exists(dataset_path)}")
                        if os.path.exists(dataset_path):
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            total_images_found = 0
                            for ext in image_extensions:
                                ext_images = list(Path(dataset_path).glob(f'*{ext}'))
                                total_images_found += len(ext_images)
                                print(f"🔍 Imágenes {ext}: {len(ext_images)}")
                            print(f"🔍 Total imágenes encontradas: {total_images_found}")
                            
                            if total_images_found > 0:
                                print(f"🔄 Iniciando procesamiento de {total_images_found} imágenes...")
                                
                            for ext in image_extensions:
                                images_with_ext = list(Path(dataset_path).glob(f'*{ext}'))
                                print(f"🔄 Procesando {len(images_with_ext)} imágenes {ext}...")
                                
                                for img_idx, image_file in enumerate(images_with_ext):
                                    print(f"📷 Procesando imagen {img_idx + 1}/{len(images_with_ext)}: {image_file.name}")
                                    
                                    # Copiar/mover imagen
                                    new_filename = get_new_filename(image_file.name, dataset_idx, processed_images)
                                    new_img_path = os.path.join(new_dataset_path, new_filename)
                                    
                                    print(f"📝 Operación {action}: {image_file} -> {new_img_path}")
                                    
                                    try:
                                        if action == 'copy':
                                            shutil.copy2(str(image_file), new_img_path)
                                        else:  # move
                                            shutil.move(str(image_file), new_img_path)
                                        
                                        print(f"✅ Imagen copiada exitosamente")
                                        
                                        # Copiar/mover etiquetas si existen
                                        label_file = image_file.with_suffix('.txt')
                                        if label_file.exists():
                                            new_label_path = os.path.splitext(new_img_path)[0] + '.txt'
                                            print(f"🏷️ Copiando etiqueta: {label_file} -> {new_label_path}")
                                            if action == 'copy':
                                                shutil.copy2(str(label_file), new_label_path)
                                            else:  # move
                                                shutil.move(str(label_file), new_label_path)
                                            print(f"✅ Etiqueta copiada exitosamente")
                                        
                                        processed_images += 1
                                        print(f"📊 Total procesadas hasta ahora: {processed_images}")
                                        
                                    except Exception as e:
                                        print(f"❌ Error procesando {image_file}: {str(e)}")
                                        continue
                
                # Si es mover, eliminar directorios vacíos
                if action == 'move':
                    for dataset in selected_datasets:
                        if dataset.get('is_subdataset', False):
                            # Para subdatasets, eliminar el directorio padre si está vacío
                            images_path = Path(dataset.get('images_path', ''))
                            labels_path = Path(dataset.get('labels_path', '')) if dataset.get('labels_path') else None
                            
                            try:
                                # Intentar eliminar directorios de imágenes y etiquetas si están vacíos
                                if images_path.exists() and not any(images_path.iterdir()):
                                    images_path.rmdir()
                                if labels_path and labels_path.exists() and not any(labels_path.iterdir()):
                                    labels_path.rmdir()
                                
                                # Intentar eliminar el directorio padre (train/valid/test) si está vacío
                                parent_dir = images_path.parent
                                if parent_dir.exists() and not any(parent_dir.iterdir()):
                                    parent_dir.rmdir()
                            except:
                                pass  # Ignorar errores al eliminar directorios
                        else:
                            # Para videos originales
                            dataset_path = os.path.join(self.dataset_path, dataset['name'])
                            try:
                                if os.path.exists(dataset_path) and not os.listdir(dataset_path):
                                    os.rmdir(dataset_path)
                            except:
                                pass  # Ignorar errores al eliminar directorios
                
                # Resetear estado de selección múltiple
                new_multi_select_data = {"active": False, "selected": []}
                
                print(f"✅ COMPLETADO: Dataset '{new_name}' creado exitosamente")
                print(f"📊 Total de imágenes procesadas: {processed_images}")
                print(f"📁 Ubicación: {new_dataset_path}")
                
                success_message = dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    f"✅ Dataset '{new_name}' creado exitosamente con {processed_images} imágenes"
                ], color="success")
                
                return 100, "100%", success_message, {"display": "block"}, new_multi_select_data
                
            except Exception as e:
                error_message = dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"❌ Error al unir datasets: {str(e)}"
                ], color="danger")
                
                return 0, "0%", error_message, {"display": "block"}, multi_select_data
        
        # Callback para refrescar la lista de videos después de una unión exitosa
        @self.app.callback(
            Output('current-page', 'data', allow_duplicate=True),
            [Input('merge-progress', 'value')],
            [State('current-page', 'data')],
            prevent_initial_call=True
        )
        def auto_refresh_after_merge(progress_value, current_page_data):
            """Refrescar automáticamente la lista después de completar la unión"""
            if progress_value == 100:
                print("🔄 Auto-refrescando lista de videos después de unión exitosa...")
                # Forzar actualización de la página actual
                if current_page_data:
                    import time
                    new_data = current_page_data.copy()
                    new_data['refresh_timestamp'] = time.time()
                    return new_data
            return no_update

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
        print(f"🏷️ Clases disponibles ({len(suite.classes)}): {', '.join(suite.classes.values())}")
        print("🌐 Abriendo en: http://localhost:8050")
        print("✅ Aplicación lista!")
        
        # Ejecutar la aplicación
        app.run(
            debug=False,  # Deshabilitar debug para evitar reinicios automáticos
            host='localhost',
            port=8050,
            dev_tools_hot_reload=False
        )
        
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()