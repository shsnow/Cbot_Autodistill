"""
Componente AutoDistill Tool - AutoDistill Suite
Interface para configurar y ejecutar AutoDistill automáticamente
"""

import dash
from dash import dcc, html, callback, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import os
import json
import subprocess
import threading
import time
from datetime import datetime

class AutoDistillComponent:
    def __init__(self, app=None):
        self.app = app
        self.available_models = {
            "GroundedSAM": {
                "name": "Grounded-SAM", 
                "description": "Modelo combinado que usa GroundingDINO + SAM para detección y segmentación precisa",
                "requires": ["groundingdino", "segment-anything"],
                "difficulty": "Avanzado",
                "speed": "Lento",
                "accuracy": "Muy Alta"
            },
            "CLIP": {
                "name": "CLIP", 
                "description": "Modelo de OpenAI para clasificación y detección basada en texto",
                "requires": ["clip"],
                "difficulty": "Fácil",
                "speed": "Rápido",
                "accuracy": "Media"
            },
            "OWL-ViT": {
                "name": "OWL-ViT",
                "description": "Modelo de detección de objetos zero-shot de Google",
                "requires": ["transformers"],
                "difficulty": "Intermedio", 
                "speed": "Medio",
                "accuracy": "Alta"
            },
            "YOLO-World": {
                "name": "YOLO-World",
                "description": "YOLO optimizado para detección zero-shot con prompts de texto",
                "requires": ["yolo-world"],
                "difficulty": "Intermedio",
                "speed": "Rápido",
                "accuracy": "Alta"
            }
        }
        
        self.processing_status = {
            "running": False,
            "progress": 0,
            "current_file": "",
            "logs": [],
            "start_time": None
        }
        
        if self.app:
            self.setup_callbacks()
    
    def get_layout(self):
        """Obtener el layout del componente"""
        return dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("🤖 AutoDistill Engine", 
                           className="text-center mb-2", 
                           style={"color": "#00d4aa", "font-weight": "bold"}),
                    html.P("Genera anotaciones automáticamente usando modelos de IA pre-entrenados",
                           className="text-center text-muted mb-4"),
                    html.Hr(style={"border-color": "#495057"})
                ])
            ]),
            
            # Pestañas
            dbc.Tabs([
                dbc.Tab(label="⚙️ Configuración", tab_id="config", active_tab_style={"background-color": "#00d4aa"}),
                dbc.Tab(label="🚀 Ejecutar", tab_id="execute", active_tab_style={"background-color": "#00d4aa"}),
                dbc.Tab(label="📊 Monitoreo", tab_id="monitor", active_tab_style={"background-color": "#00d4aa"}),
                dbc.Tab(label="📋 Historial", tab_id="history", active_tab_style={"background-color": "#00d4aa"}),
            ], id="autodistill-tabs", active_tab="config", className="mb-4"),
            
            # Contenido de pestañas
            html.Div(id="autodistill-tabs-content"),
            
            # Stores
            dcc.Store(id='autodistill-config', data={}),
            dcc.Store(id='processing-status-store', data=self.processing_status),
            
            # Interval para actualizar progreso
            dcc.Interval(id='status-interval', interval=2000, disabled=True)
            
        ], fluid=True, className="py-3")
    
    def get_config_content(self):
        """Contenido de configuración"""
        return [
            dbc.Row([
                # Configuración del modelo
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("🧠 Selección de Modelo Base", className="mb-0", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            html.Div(id="model-cards"),
                            html.Hr(),
                            dbc.Alert([
                                html.H6("💡 Recomendaciones:", className="alert-heading"),
                                html.Ul([
                                    html.Li("🚀 Para velocidad: CLIP o YOLO-World"),
                                    html.Li("🎯 Para precisión: Grounded-SAM"),
                                    html.Li("🆕 Para empezar: CLIP (más fácil de instalar)")
                                ])
                            ], color="info", className="mt-3")
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=8),
                
                # Configuración de entrada
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📁 Configuración de Entrada", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            dbc.Form([
                                dbc.Label("📂 Carpeta de imágenes:"),
                                dbc.InputGroup([
                                    dbc.Input(id="input-images-path", placeholder="Seleccionar carpeta...", readonly=True),
                                    dbc.Button("📁", id="browse-images-btn", color="outline-info")
                                ], className="mb-3"),
                                
                                dbc.Label("💾 Carpeta de salida:"),
                                dbc.InputGroup([
                                    dbc.Input(id="output-path", placeholder="Carpeta destino...", readonly=True),
                                    dbc.Button("📁", id="browse-output-btn", color="outline-info")
                                ], className="mb-3"),
                                
                                dbc.Label("🏷️ Clases a detectar (separadas por comas):"),
                                dbc.Textarea(id="classes-input", 
                                           placeholder="vehículo, persona, bicicleta, motocicleta", 
                                           value="vehículo",
                                           rows=3, className="mb-3"),
                                
                                dbc.Label("🎯 Confianza mínima:"),
                                dcc.Slider(id="confidence-slider", min=0.1, max=0.9, value=0.5, step=0.1,
                                         marks={i/10: f"{i/10}" for i in range(1, 10)}, className="mb-3"),
                                
                                dbc.Checklist([
                                    {"label": " Procesar subdirectorios", "value": "recursive"},
                                    {"label": " Crear backup de imágenes", "value": "backup"},
                                    {"label": " Generar visualizaciones", "value": "visualize"}
                                ], id="processing-options", value=["backup"])
                            ])
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=4)
            ])
        ]
    
    def get_execute_content(self):
        """Contenido de ejecución"""
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("🚀 Ejecutar AutoDistill", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            # Resumen de configuración
                            html.Div(id="config-summary"),
                            
                            html.Hr(),
                            
                            # Validación previa
                            dbc.Alert(id="validation-status", className="mb-3"),
                            
                            # Botones de control
                            dbc.ButtonGroup([
                                dbc.Button("✅ Validar Configuración", id="validate-btn", color="info", className="me-2"),
                                dbc.Button("🚀 Iniciar Procesamiento", id="start-processing-btn", color="success", size="lg", disabled=True),
                                dbc.Button("⏸️ Pausar", id="pause-btn", color="warning", disabled=True),
                                dbc.Button("🛑 Detener", id="stop-btn", color="danger", disabled=True)
                            ], className="w-100 mb-3"),
                            
                            # Estimaciones
                            dbc.Card([
                                dbc.CardHeader("📊 Estimaciones", style={"background": "#495057"}),
                                dbc.CardBody([
                                    html.Div(id="processing-estimates")
                                ], style={"background": "#2d3748"})
                            ])
                            
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ])
            ])
        ]
    
    def get_monitor_content(self):
        """Contenido de monitoreo"""
        return [
            dbc.Row([
                # Progreso en tiempo real
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📈 Progreso en Tiempo Real", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            # Barra de progreso principal
                            html.Div([
                                html.H6(id="progress-title", className="mb-2"),
                                dbc.Progress(id="main-progress", value=0, striped=True, animated=True, 
                                           color="success", className="mb-3"),
                                
                                # Estadísticas en tiempo real
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H4(id="processed-count", className="text-center text-info"),
                                                html.P("Procesadas", className="text-center text-muted small")
                                            ])
                                        ], className="text-center", style={"background": "rgba(0,123,255,0.1)"})
                                    ], width=3),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H4(id="detections-count", className="text-center text-success"),
                                                html.P("Detecciones", className="text-center text-muted small")
                                            ])
                                        ], className="text-center", style={"background": "rgba(40,167,69,0.1)"})
                                    ], width=3),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H4(id="speed-stat", className="text-center text-warning"),
                                                html.P("Img/min", className="text-center text-muted small")
                                            ])
                                        ], className="text-center", style={"background": "rgba(255,193,7,0.1)"})
                                    ], width=3),
                                    dbc.Col([
                                        dbc.Card([
                                            dbc.CardBody([
                                                html.H4(id="eta-stat", className="text-center text-info"),
                                                html.P("Tiempo rest.", className="text-center text-muted small")
                                            ])
                                        ], className="text-center", style={"background": "rgba(23,162,184,0.1)"})
                                    ], width=3)
                                ], className="g-3 mb-3"),
                                
                                # Archivo actual
                                html.Div([
                                    html.Strong("📄 Procesando: "),
                                    html.Span(id="current-file-name", className="text-muted")
                                ])
                            ])
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=8),
                
                # Panel de control en vivo
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("🎛️ Control", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            html.Div(id="live-controls"),
                            html.Hr(),
                            html.H6("📊 Recursos del Sistema:", style={"color": "#20c997"}),
                            html.Div(id="system-resources")
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=4)
            ], className="mb-4"),
            
            # Logs en tiempo real
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📜 Logs en Tiempo Real", style={"color": "#00d4aa"}),
                            dbc.ButtonGroup([
                                dbc.Button("🔄", id="refresh-logs-btn", color="outline-info", size="sm"),
                                dbc.Button("💾", id="save-logs-btn", color="outline-success", size="sm"),
                                dbc.Button("🗑️", id="clear-logs-btn", color="outline-danger", size="sm")
                            ], size="sm")
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            html.Div(id="logs-container", 
                                   style={"height": "300px", "overflow-y": "auto", 
                                         "font-family": "monospace", "font-size": "0.85rem",
                                         "background": "#0a0a0a", "padding": "1rem",
                                         "border-radius": "0.5rem"})
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ])
            ])
        ]
    
    def get_history_content(self):
        """Contenido del historial"""
        return [
            dbc.Card([
                dbc.CardHeader([
                    html.H5("📋 Historial de Ejecuciones", style={"color": "#00d4aa"})
                ], style={"background": "#2d3748"}),
                dbc.CardBody([
                    html.Div(id="execution-history"),
                    html.Div([
                        dbc.Button("🔄 Actualizar", id="refresh-history-btn", color="info", className="me-2"),
                        dbc.Button("📊 Exportar Reporte", id="export-report-btn", color="outline-primary", className="me-2"),
                        dbc.Button("🗑️ Limpiar Historial", id="clear-history-btn", color="outline-danger")
                    ], className="mt-3")
                ], style={"background": "#1a1a1a"})
            ], style={"border": "1px solid #495057"})
        ]
    
    def create_model_cards(self):
        """Crear cards de selección de modelos"""
        cards = []
        
        for model_id, model_info in self.available_models.items():
            # Colores según dificultad
            difficulty_colors = {
                "Fácil": "success",
                "Intermedio": "warning", 
                "Avanzado": "danger"
            }
            
            card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5(model_info["name"], className="card-title", style={"color": "#00d4aa"}),
                            html.P(model_info["description"], className="card-text text-muted small"),
                            
                            # Badges de características
                            html.Div([
                                dbc.Badge(f"📊 {model_info['difficulty']}", 
                                        color=difficulty_colors.get(model_info['difficulty'], 'secondary'), 
                                        className="me-1"),
                                dbc.Badge(f"⚡ {model_info['speed']}", color="info", className="me-1"),
                                dbc.Badge(f"🎯 {model_info['accuracy']}", color="success")
                            ], className="mb-2"),
                            
                            # Requisitos
                            html.Small([
                                html.Strong("Requisitos: "),
                                ", ".join(model_info["requires"])
                            ], className="text-muted")
                        ], width=9),
                        dbc.Col([
                            dbc.Button("Seleccionar", 
                                     id={"type": "model-select", "model": model_id},
                                     color="outline-primary", 
                                     className="w-100")
                        ], width=3)
                    ])
                ])
            ], className="mb-3", 
               style={"border": "1px solid #495057", "background": "#2d3748"})
            
            cards.append(card)
        
        return cards
    
    def setup_callbacks(self):
        """Configurar callbacks del componente"""
        
        @self.app.callback(
            Output('autodistill-tabs-content', 'children'),
            Input('autodistill-tabs', 'active_tab')
        )
        def update_tab_content(active_tab):
            if active_tab == "config":
                return self.get_config_content()
            elif active_tab == "execute":
                return self.get_execute_content()
            elif active_tab == "monitor":
                return self.get_monitor_content()
            elif active_tab == "history":
                return self.get_history_content()
            return html.Div()
        
        @self.app.callback(
            Output('model-cards', 'children'),
            Input('autodistill-tabs', 'active_tab')
        )
        def update_model_cards(active_tab):
            if active_tab == "config":
                return self.create_model_cards()
            return []
        
        # Callback para selección de modelo
        @self.app.callback(
            Output('autodistill-config', 'data'),
            Input({'type': 'model-select', 'model': ALL}, 'n_clicks'),
            State('autodistill-config', 'data')
        )
        def select_model(model_clicks, current_config):
            if any(model_clicks):
                ctx = dash.callback_context
                if ctx.triggered:
                    button_info = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
                    selected_model = button_info['model']
                    
                    current_config = current_config or {}
                    current_config['selected_model'] = selected_model
                    current_config['model_info'] = self.available_models[selected_model]
                    
                    return current_config
            
            return current_config or {}
        
        # Otros callbacks básicos para demostración
        @self.app.callback(
            Output('config-summary', 'children'),
            Input('autodistill-config', 'data')
        )
        def update_config_summary(config):
            if not config or 'selected_model' not in config:
                return dbc.Alert("⚠️ Selecciona un modelo primero", color="warning")
            
            model_info = config.get('model_info', {})
            return dbc.Card([
                dbc.CardBody([
                    html.H6("📝 Configuración Actual:", style={"color": "#00d4aa"}),
                    html.Ul([
                        html.Li(f"🧠 Modelo: {model_info.get('name', 'N/A')}"),
                        html.Li(f"📊 Dificultad: {model_info.get('difficulty', 'N/A')}"),
                        html.Li(f"⚡ Velocidad: {model_info.get('speed', 'N/A')}"),
                        html.Li(f"🎯 Precisión: {model_info.get('accuracy', 'N/A')}")
                    ])
                ])
            ], style={"background": "rgba(0,212,170,0.1)", "border": "1px solid #00d4aa"})