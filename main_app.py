"""
AutoDistill Suite - Aplicación Principal
Plataforma completa para etiquetado automático y corrección de anotaciones
"""

import dash
from dash import dcc, html, callback, Input, Output, State, clientside_callback
import dash_bootstrap_components as dbc
from datetime import datetime
import os
import sys

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports de componentes
try:
    from components.annotation_tool import AnnotationToolComponent
    from components.autodistill_tool import AutoDistillComponent
    from components.file_manager import FileManagerComponent
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Algunos componentes no están disponibles: {e}")
    COMPONENTS_AVAILABLE = False

class AutoDistillSuite:
    def __init__(self):
        self.app = dash.Dash(__name__, 
                           external_stylesheets=[dbc.themes.CYBORG],
                           assets_folder='assets')
        self.app.title = "AutoDistill Suite - Plataforma de Etiquetado Automático"
        
        # Inicializar componentes
        if COMPONENTS_AVAILABLE:
            self.annotation_component = AnnotationToolComponent(self.app)
            self.autodistill_component = AutoDistillComponent(self.app)
            self.file_component = FileManagerComponent(self.app)
        else:
            self.annotation_component = None
            self.autodistill_component = None
            self.file_component = None
        
        # Configuración de la app
        self.setup_layout()
        self.setup_callbacks()
    
    def get_navbar(self):
        """Crear navbar principal"""
        return dbc.Navbar([
            dbc.Container([
                # Brand
                dbc.Row([
                    dbc.Col([
                        html.Img(src="/assets/logo.png", height="40px", className="me-2", 
                                style={"filter": "brightness(0) saturate(100%) invert(64%) sepia(79%) saturate(2476%) hue-rotate(133deg) brightness(101%) contrast(101%)"}),
                        dbc.NavbarBrand("AutoDistill Suite", className="ms-2 fw-bold", 
                                      style={"color": "#00d4aa", "font-family": "Arial Black", "font-size": "1.5rem"})
                    ], width="auto"),
                ], align="center", className="g-0"),
                
                # Navigation items
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("🏠 Inicio", id="nav-home", href="#", active=True, 
                                          className="text-light fw-bold mx-2")),
                    dbc.NavItem(dbc.NavLink("🏷️ Etiquetado", id="nav-annotation", href="#", 
                                          className="text-light fw-bold mx-2")),
                    dbc.NavItem(dbc.NavLink("🤖 AutoDistill", id="nav-autodistill", href="#", 
                                          className="text-light fw-bold mx-2")),
                    dbc.NavItem(dbc.NavLink("📁 Archivos", id="nav-files", href="#", 
                                          className="text-light fw-bold mx-2")),
                ], navbar=True, className="ms-auto"),
            ], fluid=True)
        ], color="dark", dark=True, className="mb-3", 
           style={"background": "linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)", 
                  "border-bottom": "2px solid #00d4aa"})
    
    def get_home_content(self):
        """Contenido de la página de inicio"""
        return dbc.Container([
            # Header Hero
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1("🚀 AutoDistill Suite", 
                               className="display-3 fw-bold text-center mb-3",
                               style={"color": "#00d4aa", "text-shadow": "0 0 20px rgba(0,212,170,0.5)"}),
                        html.P("Plataforma completa para etiquetado automático y corrección de anotaciones",
                               className="lead text-center text-light mb-4", 
                               style={"font-size": "1.3rem"}),
                        html.Hr(className="my-4", style={"border-color": "#00d4aa", "border-width": "3px"}),
                        
                        # Estadísticas rápidas
                        dbc.Row([
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H4("📊", className="card-title text-center", style={"font-size": "3rem"}),
                                        html.H5("Proyectos", className="text-center text-muted"),
                                        html.H3("0", className="text-center text-info fw-bold")
                                    ])
                                ], className="h-100 shadow-lg", style={"background": "rgba(0,212,170,0.1)", "border": "1px solid #00d4aa"})
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H4("🖼️", className="card-title text-center", style={"font-size": "3rem"}),
                                        html.H5("Imágenes", className="text-center text-muted"),
                                        html.H3("0", className="text-center text-warning fw-bold")
                                    ])
                                ], className="h-100 shadow-lg", style={"background": "rgba(255,193,7,0.1)", "border": "1px solid #ffc107"})
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H4("🏷️", className="card-title text-center", style={"font-size": "3rem"}),
                                        html.H5("Anotaciones", className="text-center text-muted"),
                                        html.H3("0", className="text-center text-success fw-bold")
                                    ])
                                ], className="h-100 shadow-lg", style={"background": "rgba(40,167,69,0.1)", "border": "1px solid #28a745"})
                            ], width=3),
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardBody([
                                        html.H4("⏱️", className="card-title text-center", style={"font-size": "3rem"}),
                                        html.H5("Tiempo Ahorrado", className="text-center text-muted"),
                                        html.H3("0h", className="text-center text-danger fw-bold")
                                    ])
                                ], className="h-100 shadow-lg", style={"background": "rgba(220,53,69,0.1)", "border": "1px solid #dc3545"})
                            ], width=3),
                        ], className="g-4 mb-5")
                    ], className="text-center py-5",
                       style={"background": "linear-gradient(135deg, rgba(0,212,170,0.05) 0%, rgba(0,212,170,0.1) 100%)",
                              "border-radius": "2rem", "border": "1px solid rgba(0,212,170,0.2)"})
                ])
            ], className="mb-5"),
            
            # Herramientas principales
            dbc.Row([
                dbc.Col([
                    html.H2("🛠️ Herramientas Principales", className="text-center mb-4", 
                           style={"color": "#00d4aa", "font-weight": "bold"})
                ])
            ]),
            
            dbc.Row([
                # Etiquetado CVAT
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.H1("🏷️", className="text-center mb-3", style={"font-size": "4rem"}),
                                html.H4("Corrección de Etiquetado", className="card-title text-center fw-bold"),
                                html.P("Herramienta similar a CVAT para corregir y editar anotaciones YOLO de manera interactiva.",
                                      className="card-text text-center"),
                                html.Ul([
                                    html.Li("✏️ Edición interactiva de bounding boxes"),
                                    html.Li("⌨️ Atajos de teclado (F/D para navegación)"),
                                    html.Li("💾 Guardado automático"),
                                    html.Li("🎨 Interface oscura moderna"),
                                ], className="text-start mb-4"),
                                dbc.Button("Abrir Herramienta", id="btn-annotation-tool", 
                                         color="info", size="lg", className="w-100 fw-bold shadow-lg",
                                         style={"background": "linear-gradient(135deg, #00d4aa 0%, #20c997 100%)",
                                               "border": "none"})
                            ])
                        ])
                    ], className="h-100 shadow-lg hover-card", 
                       style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)",
                              "border": "1px solid #00d4aa", "border-radius": "1rem"})
                ], width=4),
                
                # AutoDistill
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.H1("🤖", className="text-center mb-3", style={"font-size": "4rem"}),
                                html.H4("AutoDistill Engine", className="card-title text-center fw-bold"),
                                html.P("Genera anotaciones automáticamente usando modelos pre-entrenados en tus videos o imágenes.",
                                      className="card-text text-center"),
                                html.Ul([
                                    html.Li("🎥 Procesamiento de videos automático"),
                                    html.Li("🧠 Múltiples modelos base disponibles"),
                                    html.Li("⚙️ Configuración avanzada"),
                                    html.Li("📊 Monitoreo de progreso en tiempo real"),
                                ], className="text-start mb-4"),
                                dbc.Button("Iniciar AutoDistill", id="btn-autodistill-tool", 
                                         color="warning", size="lg", className="w-100 fw-bold shadow-lg",
                                         style={"background": "linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)",
                                               "border": "none", "color": "#000"})
                            ])
                        ])
                    ], className="h-100 shadow-lg hover-card",
                       style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)",
                              "border": "1px solid #ffc107", "border-radius": "1rem"})
                ], width=4),
                
                # Gestión de Archivos
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.H1("📁", className="text-center mb-3", style={"font-size": "4rem"}),
                                html.H4("Gestión de Archivos", className="card-title text-center fw-bold"),
                                html.P("Selecciona y organiza tus carpetas, videos e imágenes para el procesamiento.",
                                      className="card-text text-center"),
                                html.Ul([
                                    html.Li("📂 Explorador de carpetas intuitivo"),
                                    html.Li("🎬 Soporte para múltiples formatos de video"),
                                    html.Li("🖼️ Vista previa de imágenes"),
                                    html.Li("📋 Gestión de datasets"),
                                ], className="text-start mb-4"),
                                dbc.Button("Explorar Archivos", id="btn-file-manager", 
                                         color="success", size="lg", className="w-100 fw-bold shadow-lg",
                                         style={"background": "linear-gradient(135deg, #28a745 0%, #20c997 100%)",
                                               "border": "none"})
                            ])
                        ])
                    ], className="h-100 shadow-lg hover-card",
                       style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)",
                              "border": "1px solid #28a745", "border-radius": "1rem"})
                ], width=4),
            ], className="g-4 mb-5"),
            
            # Workflow sugerido
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("🔄 Flujo de Trabajo Recomendado", className="mb-0 text-center fw-bold",
                                   style={"color": "#00d4aa"})
                        ], style={"background": "linear-gradient(135deg, #1a1a1a 0%, #2d3748 100%)", 
                                 "border-bottom": "1px solid #00d4aa"}),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.Div([
                                        html.H1("1️⃣", className="text-center mb-2"),
                                        html.H5("Seleccionar Material", className="text-center fw-bold"),
                                        html.P("Usa la Gestión de Archivos para seleccionar tus videos o carpetas de imágenes.",
                                              className="text-center small")
                                    ], className="p-3 rounded",
                                       style={"background": "rgba(40,167,69,0.1)", "border": "1px solid #28a745"})
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.H1("2️⃣", className="text-center mb-2"),
                                        html.H5("Generar Anotaciones", className="text-center fw-bold"),
                                        html.P("Ejecuta AutoDistill para generar anotaciones automáticas en tu material.",
                                              className="text-center small")
                                    ], className="p-3 rounded",
                                       style={"background": "rgba(255,193,7,0.1)", "border": "1px solid #ffc107"})
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.H1("3️⃣", className="text-center mb-2"),
                                        html.H5("Revisar y Corregir", className="text-center fw-bold"),
                                        html.P("Usa la herramienta de Etiquetado para revisar y corregir las anotaciones.",
                                              className="text-center small")
                                    ], className="p-3 rounded",
                                       style={"background": "rgba(0,212,170,0.1)", "border": "1px solid #00d4aa"})
                                ], width=3),
                                dbc.Col([
                                    html.Div([
                                        html.H1("4️⃣", className="text-center mb-2"),
                                        html.H5("Dataset Listo", className="text-center fw-bold"),
                                        html.P("Tu dataset estará listo para entrenar modelos de detección de objetos.",
                                              className="text-center small")
                                    ], className="p-3 rounded",
                                       style={"background": "rgba(220,53,69,0.1)", "border": "1px solid #dc3545"})
                                ], width=3),
                            ], className="g-3")
                        ], style={"background": "#1a1a1a"})
                    ], style={"background": "#1a1a1a", "border": "1px solid #495057", "border-radius": "1rem"})
                ])
            ], className="mb-5"),
            
            # Footer info
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.P([
                            "🚀 ", html.Strong("AutoDistill Suite"), " - Desarrollado para acelerar el proceso de creación de datasets de detección de objetos."
                        ], className="text-center text-muted mb-2"),
                        html.P([
                            "⚡ Ahorra horas de trabajo manual • 🎯 Precisión mejorada • 🛠️ Herramientas profesionales"
                        ], className="text-center text-muted small")
                    ], className="py-3")
                ])
            ])
            
        ], fluid=True, className="py-4")
    
    def setup_layout(self):
        """Configurar el layout principal"""
        self.app.layout = html.Div([
            # Store para el estado de navegación
            dcc.Store(id='current-page', data='home'),
            
            # Navbar
            html.Div(id="navbar-container"),
            
            # Contenido principal
            html.Div(id="page-content"),
            

            
        ], style={'background': 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%)', 'min-height': '100vh'})
    
    def setup_callbacks(self):
        """Configurar callbacks principales"""
        
        @self.app.callback(
            Output('navbar-container', 'children'),
            Input('current-page', 'data')
        )
        def update_navbar(current_page):
            return self.get_navbar()
        
        @self.app.callback(
            [Output('page-content', 'children'),
             Output('current-page', 'data')],
            [Input('nav-home', 'n_clicks'),
             Input('nav-annotation', 'n_clicks'),
             Input('nav-autodistill', 'n_clicks'),
             Input('nav-files', 'n_clicks'),
             Input('btn-annotation-tool', 'n_clicks'),
             Input('btn-autodistill-tool', 'n_clicks'),
             Input('btn-file-manager', 'n_clicks')],
            [State('current-page', 'data')]
        )
        def navigate_pages(nav_home, nav_annotation, nav_autodistill, nav_files,
                          btn_annotation, btn_autodistill, btn_files, current_page):
            """Manejar navegación entre páginas"""
            ctx = dash.callback_context
            if not ctx.triggered:
                return self.get_home_content(), 'home'
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id in ['nav-home']:
                return self.get_home_content(), 'home'
            elif button_id in ['nav-annotation', 'btn-annotation-tool']:
                return self.get_annotation_content(), 'annotation'
            elif button_id in ['nav-autodistill', 'btn-autodistill-tool']:
                return self.get_autodistill_content(), 'autodistill'
            elif button_id in ['nav-files', 'btn-file-manager']:
                return self.get_files_content(), 'files'
            else:
                return self.get_home_content(), 'home'
    
    def get_annotation_content(self):
        """Contenido de la herramienta de anotación"""
        if self.annotation_component and COMPONENTS_AVAILABLE:
            # Obtener dataset seleccionado (por defecto usar dataset_cruce_3 por compatibilidad)
            dataset_path = "dataset_cruce_3"
            return self.annotation_component.get_layout(dataset_path)
        else:
            return dbc.Container([
                dbc.Alert([
                    html.H4("🏷️ Herramienta de Etiquetado - No Disponible", className="alert-heading"),
                    html.P("Los componentes no se pudieron cargar correctamente."),
                    html.Hr(),
                    html.P("Verifica que todos los archivos estén en su lugar", className="mb-0")
                ], color="warning", className="text-center")
            ], className="py-5")
    
    def get_autodistill_content(self):
        """Contenido de AutoDistill"""
        if self.autodistill_component and COMPONENTS_AVAILABLE:
            return self.autodistill_component.get_layout()
        else:
            return dbc.Container([
                dbc.Alert([
                    html.H4("🤖 AutoDistill Engine - No Disponible", className="alert-heading"),
                    html.P("Los componentes no se pudieron cargar correctamente."),
                    html.Hr(),
                    html.P("Verifica que todos los archivos estén en su lugar", className="mb-0")
                ], color="warning", className="text-center")
            ], className="py-5")
    
    def get_files_content(self):
        """Contenido de gestión de archivos"""
        if self.file_component and COMPONENTS_AVAILABLE:
            return self.file_component.get_layout()
        else:
            return dbc.Container([
                dbc.Alert([
                    html.H4("📁 Gestión de Archivos - No Disponible", className="alert-heading"),
                    html.P("Los componentes no se pudieron cargar correctamente."),
                    html.Hr(),
                    html.P("Verifica que todos los archivos estén en su lugar", className="mb-0")
                ], color="warning", className="text-center")
            ], className="py-5")
    
    def run(self, debug=True, port=8050, host='127.0.0.1'):
        """Ejecutar la aplicación"""
        print("🚀 Iniciando AutoDistill Suite...")
        print(f"🌐 Servidor iniciando en: http://{host}:{port}")
        print("=" * 60)
        print("📱 NAVEGACIÓN:")
        print("  • 🏠 Inicio - Dashboard principal con estadísticas")
        print("  • 🏷️ Etiquetado - Herramienta de corrección estilo CVAT")
        print("  • 🤖 AutoDistill - Motor de anotación automática")
        print("  • 📁 Archivos - Gestión de datasets y proyectos")
        print("=" * 60)
        
        self.app.run_server(debug=debug, port=port, host=host)

if __name__ == "__main__":
    try:
        app = AutoDistillSuite()
        app.run(debug=False, port=8050)
    except Exception as e:
        print(f"❌ Error iniciando la aplicación: {e}")