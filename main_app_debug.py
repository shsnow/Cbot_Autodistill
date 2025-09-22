"""
AutoDistill Suite - Aplicación Principal (Versión Simplificada para Debug)
"""

import dash
from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from datetime import datetime
import os

class AutoDistillSuite:
    def __init__(self):
        self.app = dash.Dash(__name__, 
                           external_stylesheets=[dbc.themes.CYBORG],
                           assets_folder='assets')
        self.app.title = "AutoDistill Suite - Debug Version"
        
        # Configuración de la app
        self.setup_layout()
        self.setup_callbacks()
    
    def get_navbar(self):
        """Crear navbar principal"""
        return dbc.Navbar([
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        dbc.NavbarBrand("🚀 AutoDistill Suite", className="fw-bold", 
                                      style={"color": "#00d4aa", "font-size": "1.5rem"})
                    ], width="auto"),
                ], align="center"),
                
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
        ], color="dark", dark=True, className="mb-3")
    
    def get_home_content(self):
        """Contenido de la página de inicio"""
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 AutoDistill Suite", 
                           className="display-3 fw-bold text-center mb-3",
                           style={"color": "#00d4aa"}),
                    html.P("Plataforma completa para etiquetado automático y corrección de anotaciones",
                           className="lead text-center text-light mb-4"),
                    
                    # Botones de herramientas
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H1("🏷️", className="text-center mb-3", style={"font-size": "4rem"}),
                                    html.H4("Corrección de Etiquetado", className="card-title text-center fw-bold text-light"),
                                    html.P("Herramienta similar a CVAT para corregir anotaciones YOLO.",
                                          className="card-text text-center text-muted"),
                                    dbc.Button("Abrir Herramienta", id="btn-annotation-tool", 
                                             color="info", size="lg", className="w-100 fw-bold")
                                ])
                            ], className="h-100", style={"background": "#2d3748", "border": "1px solid #00d4aa"})
                        ], width=4),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H1("🤖", className="text-center mb-3", style={"font-size": "4rem"}),
                                    html.H4("AutoDistill Engine", className="card-title text-center fw-bold text-light"),
                                    html.P("Genera anotaciones automáticamente usando modelos pre-entrenados.",
                                          className="card-text text-center text-muted"),
                                    dbc.Button("Iniciar AutoDistill", id="btn-autodistill-tool", 
                                             color="warning", size="lg", className="w-100 fw-bold")
                                ])
                            ], className="h-100", style={"background": "#2d3748", "border": "1px solid #ffc107"})
                        ], width=4),
                        
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H1("📁", className="text-center mb-3", style={"font-size": "4rem"}),
                                    html.H4("Gestión de Archivos", className="card-title text-center fw-bold text-light"),
                                    html.P("Selecciona y organiza tus carpetas, videos e imágenes.",
                                          className="card-text text-center text-muted"),
                                    dbc.Button("Explorar Archivos", id="btn-file-manager", 
                                             color="success", size="lg", className="w-100 fw-bold")
                                ])
                            ], className="h-100", style={"background": "#2d3748", "border": "1px solid #28a745"})
                        ], width=4),
                    ], className="g-4 mb-5"),
                    
                    # Información del sistema
                    dbc.Alert([
                        html.H5("✅ Sistema Funcionando Correctamente", className="alert-heading text-success"),
                        html.P("La aplicación base está cargando correctamente."),
                        html.Hr(),
                        html.P(f"Tiempo de carga: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="mb-0 small")
                    ], color="success", className="mt-4")
                ])
            ])
        ], fluid=True, className="py-4")
    
    def get_placeholder_content(self, title, description):
        """Contenido placeholder para secciones"""
        return dbc.Container([
            dbc.Alert([
                html.H4(f"{title} - En Construcción", className="alert-heading"),
                html.P(description),
                html.Hr(),
                dbc.Button("← Volver al Inicio", id="back-home", color="primary", size="sm")
            ], color="info", className="text-center")
        ], className="py-5")
    
    def setup_layout(self):
        """Configurar el layout principal"""
        self.app.layout = html.Div([
            # Store para el estado de navegación
            dcc.Store(id='current-page', data='home'),
            
            # Navbar
            html.Div(id="navbar-container"),
            
            # Contenido principal
            html.Div(id="page-content", style={"min-height": "80vh"}),
            
        ], style={
            'background': '#1a1a1a', 
            'min-height': '100vh',
            'color': '#e2e8f0'
        })
    
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
             Input('btn-file-manager', 'n_clicks'),
             Input('back-home', 'n_clicks')],
            [State('current-page', 'data')]
        )
        def navigate_pages(nav_home, nav_annotation, nav_autodistill, nav_files,
                          btn_annotation, btn_autodistill, btn_files, back_home, current_page):
            """Manejar navegación entre páginas"""
            if not ctx.triggered:
                return self.get_home_content(), 'home'
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id in ['nav-home', 'back-home']:
                return self.get_home_content(), 'home'
            elif button_id in ['nav-annotation', 'btn-annotation-tool']:
                content = self.get_placeholder_content("🏷️ Herramienta de Etiquetado", 
                                                     "Esta sección contendrá tu herramienta de corrección de etiquetado.")
                return content, 'annotation'
            elif button_id in ['nav-autodistill', 'btn-autodistill-tool']:
                content = self.get_placeholder_content("🤖 AutoDistill Engine", 
                                                     "Esta sección contendrá la interfaz para AutoDistill.")
                return content, 'autodistill'
            elif button_id in ['nav-files', 'btn-file-manager']:
                content = self.get_placeholder_content("📁 Gestión de Archivos", 
                                                     "Esta sección contendrá el explorador de archivos.")
                return content, 'files'
            else:
                return self.get_home_content(), 'home'
    
    def run(self, debug=True, port=8050, host='127.0.0.1'):
        """Ejecutar la aplicación"""
        print("🚀 Iniciando AutoDistill Suite (Versión Debug)...")
        print(f"🌐 Servidor iniciando en: http://{host}:{port}")
        print("=" * 60)
        print("🔍 MODO DEBUG - Versión simplificada para pruebas")
        print("=" * 60)
        
        self.app.run_server(debug=debug, port=port, host=host)

if __name__ == "__main__":
    try:
        app = AutoDistillSuite()
        app.run(debug=True, port=8050)
    except Exception as e:
        print(f"❌ Error iniciando la aplicación: {e}")
        import traceback
        traceback.print_exc()