"""
Componente de Gestión de Archivos - AutoDistill Suite
Permite seleccionar carpetas, videos y organizar datasets
"""

import dash
from dash import dcc, html, callback, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import os
import json
from pathlib import Path
import cv2
from datetime import datetime
import shutil

class FileManagerComponent:
    def __init__(self, app=None):
        self.app = app
        self.current_directory = os.path.expanduser("~")  # Directorio home por defecto
        self.selected_items = []
        self.projects = self.load_projects()
        
        if self.app:
            self.setup_callbacks()
    
    def load_projects(self):
        """Cargar proyectos guardados"""
        projects_file = "projects.json"
        if os.path.exists(projects_file):
            try:
                with open(projects_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_projects(self):
        """Guardar proyectos"""
        try:
            with open("projects.json", 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando proyectos: {e}")
    
    def get_layout(self):
        """Obtener el layout del componente"""
        return dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H2("📁 Gestión de Archivos y Proyectos", 
                           className="text-center mb-3", 
                           style={"color": "#00d4aa", "font-weight": "bold"}),
                    html.P("Organiza tus datasets, selecciona videos para procesar y gestiona proyectos",
                           className="text-center text-muted mb-4"),
                    html.Hr(style={"border-color": "#495057"})
                ])
            ]),
            
            # Pestañas principales
            dbc.Tabs([
                # Pestaña de explorador de archivos
                dbc.Tab(label="🗂️ Explorador", tab_id="explorer", active_tab_style={"background-color": "#00d4aa"}),
                # Pestaña de proyectos
                dbc.Tab(label="📋 Proyectos", tab_id="projects", active_tab_style={"background-color": "#00d4aa"}),
                # Pestaña de procesamiento
                dbc.Tab(label="⚙️ Procesar", tab_id="process", active_tab_style={"background-color": "#00d4aa"}),
            ], id="file-tabs", active_tab="explorer", className="mb-4"),
            
            # Contenido de pestañas
            html.Div(id="file-tabs-content"),
            
            # Store para datos
            dcc.Store(id='current-directory-store', data=self.current_directory),
            dcc.Store(id='selected-files-store', data=[]),
            dcc.Store(id='projects-store', data=self.projects),
            
        ], fluid=True, className="py-3")
    
    def get_explorer_content(self):
        """Contenido del explorador de archivos"""
        return [
            # Navegación de directorios
            dbc.Card([
                dbc.CardHeader([
                    html.H5("📂 Navegador de Directorios", className="mb-0", style={"color": "#00d4aa"})
                ], style={"background": "#2d3748"}),
                dbc.CardBody([
                    # Breadcrumb
                    dbc.Row([
                        dbc.Col([
                            html.Label("📍 Directorio actual:", className="mb-2", style={"color": "#00d4aa"}),
                            dbc.InputGroup([
                                dbc.Input(id="current-path", value=self.current_directory, readonly=True),
                                dbc.Button("🏠", id="home-btn", color="outline-info", size="sm", title="Ir a inicio"),
                                dbc.Button("⬆️", id="parent-btn", color="outline-info", size="sm", title="Subir un nivel"),
                                dbc.Button("🔄", id="refresh-btn", color="outline-info", size="sm", title="Actualizar")
                            ])
                        ], width=10),
                        dbc.Col([
                            html.Label("Acciones:", className="mb-2", style={"color": "#00d4aa"}),
                            dbc.ButtonGroup([
                                dbc.Button("📁 Nueva Carpeta", id="new-folder-btn", color="success", size="sm"),
                            ], className="w-100")
                        ], width=2)
                    ], className="mb-3"),
                    
                    # Lista de archivos y carpetas
                    html.Div(id="file-list-container", style={"max-height": "400px", "overflow-y": "auto"})
                    
                ], style={"background": "#1a1a1a"})
            ], className="mb-4", style={"border": "1px solid #495057"}),
            
            # Panel de selección
            dbc.Card([
                dbc.CardHeader([
                    html.H5("✅ Archivos Seleccionados", className="mb-0", style={"color": "#00d4aa"}),
                    dbc.Badge(id="selection-count", color="info", className="ms-2")
                ], style={"background": "#2d3748"}),
                dbc.CardBody([
                    html.Div(id="selected-files-list", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("🗑️ Limpiar Selección", id="clear-selection", color="outline-danger", size="sm")
                        ], width=6),
                        dbc.Col([
                            dbc.Button("💾 Crear Proyecto", id="create-project-btn", color="primary", size="sm", className="w-100")
                        ], width=6)
                    ])
                ], style={"background": "#1a1a1a"})
            ], className="mb-4", style={"border": "1px solid #495057"})
        ]
    
    def get_projects_content(self):
        """Contenido de la gestión de proyectos"""
        return [
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📋 Mis Proyectos", className="mb-0", style={"color": "#00d4aa"}),
                            dbc.Badge(f"{len(self.projects)} proyectos", color="info", className="ms-2")
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            html.Div(id="projects-list"),
                            html.Div([
                                dbc.Button("➕ Nuevo Proyecto", id="new-project-btn", color="success", className="me-2"),
                                dbc.Button("📤 Importar", id="import-project-btn", color="info", className="me-2"),
                                dbc.Button("💾 Exportar Todo", id="export-projects-btn", color="outline-primary")
                            ], className="mt-3")
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=8),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📊 Estadísticas", style={"color": "#00d4aa"})
                        ], style={"background": "#2d3748"}),
                        dbc.CardBody([
                            html.Div(id="project-stats")
                        ], style={"background": "#1a1a1a"})
                    ], style={"border": "1px solid #495057"})
                ], width=4)
            ])
        ]
    
    def get_process_content(self):
        """Contenido del procesador de videos"""
        return [
            dbc.Card([
                dbc.CardHeader([
                    html.H5("⚙️ Procesamiento de Videos y Preparación de Datasets", 
                           className="mb-0", style={"color": "#00d4aa"})
                ], style={"background": "#2d3748"}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H6("🎥 Extracción de Frames", className="mb-3", style={"color": "#20c997"}),
                            dbc.Form([
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Video de entrada:"),
                                        dbc.Input(id="video-input-path", placeholder="Selecciona un video...", readonly=True),
                                        dbc.Button("📁 Seleccionar Video", id="select-video-btn", color="outline-info", size="sm", className="mt-2")
                                    ], width=12),
                                ], className="mb-3"),
                                
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Intervalo de frames:"),
                                        dbc.Input(id="frame-interval", type="number", value=30, min=1, max=300),
                                        dbc.FormText("Extraer 1 frame cada N frames")
                                    ], width=6),
                                    dbc.Col([
                                        dbc.Label("Carpeta de salida:"),
                                        dbc.Input(id="output-folder", placeholder="Carpeta destino...", readonly=True),
                                        dbc.Button("📁 Seleccionar", id="select-output-btn", color="outline-info", size="sm", className="mt-2")
                                    ], width=6)
                                ], className="mb-3"),
                                
                                dbc.Button("🎬 Extraer Frames", id="extract-frames-btn", color="primary", size="lg", className="w-100")
                            ])
                        ], width=6),
                        
                        dbc.Col([
                            html.H6("📁 Preparación de Dataset", className="mb-3", style={"color": "#ffc107"}),
                            dbc.Form([
                                dbc.Label("Estructura de Dataset:"),
                                dbc.RadioItems(
                                    options=[
                                        {"label": "YOLO (train/val/test)", "value": "yolo"},
                                        {"label": "COCO Format", "value": "coco"},
                                        {"label": "Custom", "value": "custom"}
                                    ],
                                    value="yolo",
                                    id="dataset-format",
                                    className="mb-3"
                                ),
                                
                                dbc.Label("División del dataset:"),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Train %:", size="sm"),
                                        dbc.Input(type="number", value=70, min=10, max=90, id="train-split")
                                    ], width=4),
                                    dbc.Col([
                                        dbc.Label("Val %:", size="sm"),
                                        dbc.Input(type="number", value=20, min=5, max=40, id="val-split")
                                    ], width=4),
                                    dbc.Col([
                                        dbc.Label("Test %:", size="sm"),
                                        dbc.Input(type="number", value=10, min=5, max=40, id="test-split")
                                    ], width=4)
                                ], className="mb-3"),
                                
                                dbc.Button("📦 Crear Dataset", id="create-dataset-btn", color="warning", size="lg", className="w-100")
                            ])
                        ], width=6)
                    ])
                ], style={"background": "#1a1a1a"})
            ], style={"border": "1px solid #495057"}),
            
            # Panel de progreso
            dbc.Card([
                dbc.CardHeader([
                    html.H5("📊 Progreso de Procesamiento", style={"color": "#00d4aa"})
                ], style={"background": "#2d3748"}),
                dbc.CardBody([
                    html.Div(id="processing-progress"),
                    dcc.Interval(id="progress-interval", interval=1000, disabled=True)
                ], style={"background": "#1a1a1a"})
            ], className="mt-4", style={"border": "1px solid #495057"})
        ]
    
    def get_directory_contents(self, directory):
        """Obtener contenido de un directorio"""
        try:
            items = []
            # Agregar entrada para directorio padre si no estamos en la raíz
            parent_dir = os.path.dirname(directory)
            if parent_dir != directory:  # No estamos en la raíz
                items.append({
                    'name': '.. (Subir)',
                    'type': 'parent',
                    'path': parent_dir,
                    'size': '',
                    'modified': ''
                })
            
            # Listar contenido del directorio
            for item_name in sorted(os.listdir(directory)):
                item_path = os.path.join(directory, item_name)
                try:
                    stat = os.stat(item_path)
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    
                    if os.path.isdir(item_path):
                        items.append({
                            'name': item_name,
                            'type': 'folder',
                            'path': item_path,
                            'size': '—',
                            'modified': modified
                        })
                    else:
                        # Determinar tipo de archivo
                        ext = os.path.splitext(item_name)[1].lower()
                        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
                            file_type = 'video'
                        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
                            file_type = 'image'
                        else:
                            file_type = 'file'
                        
                        # Tamaño del archivo
                        size = stat.st_size
                        if size > 1024*1024*1024:  # GB
                            size_str = f"{size/(1024*1024*1024):.1f} GB"
                        elif size > 1024*1024:  # MB
                            size_str = f"{size/(1024*1024):.1f} MB"
                        elif size > 1024:  # KB
                            size_str = f"{size/1024:.1f} KB"
                        else:
                            size_str = f"{size} B"
                        
                        items.append({
                            'name': item_name,
                            'type': file_type,
                            'path': item_path,
                            'size': size_str,
                            'modified': modified
                        })
                except (PermissionError, OSError):
                    continue
            
            return items
        except (PermissionError, OSError):
            return []
    
    def create_file_list_items(self, items, selected_files):
        """Crear elementos de la lista de archivos"""
        if not items:
            return dbc.Alert("📭 Carpeta vacía o sin permisos de acceso", color="info")
        
        file_items = []
        
        for item in items:
            # Iconos según el tipo
            icons = {
                'parent': '⬆️',
                'folder': '📁',
                'video': '🎥',
                'image': '🖼️',
                'file': '📄'
            }
            
            icon = icons.get(item['type'], '📄')
            
            # Determinar si está seleccionado
            is_selected = item['path'] in selected_files
            
            # Color según el tipo
            colors = {
                'parent': 'outline-secondary',
                'folder': 'outline-primary',
                'video': 'outline-warning',
                'image': 'outline-success',
                'file': 'outline-info'
            }
            
            color = colors.get(item['type'], 'outline-info')
            if is_selected:
                color = color.replace('outline-', '')
            
            file_items.append(
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Span([
                                    icon, " ", 
                                    html.Strong(item['name'], 
                                              style={"color": "#00d4aa" if item['type'] == 'folder' else "#adb5bd"})
                                ]),
                                html.Br(),
                                html.Small([
                                    f"📏 {item['size']} • 🕒 {item['modified']}"
                                ], className="text-muted")
                            ], width=8),
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button(
                                        "✓" if is_selected else ("📂" if item['type'] in ['folder', 'parent'] else "➕"),
                                        id={"type": "file-item", "path": item['path'], "action": "select"},
                                        color=color,
                                        size="sm"
                                    ) if item['type'] != 'parent' else dbc.Button(
                                        "📂",
                                        id={"type": "file-item", "path": item['path'], "action": "navigate"},
                                        color="outline-secondary",
                                        size="sm"
                                    )
                                ])
                            ], width=4, className="text-end")
                        ], align="center")
                    ], className="py-2")
                ], className="mb-2", 
                   style={"border": f"1px solid {'#00d4aa' if is_selected else '#495057'}", 
                         "background": "rgba(0,212,170,0.1)" if is_selected else "#2d3748"})
            )
        
        return file_items
    
    def setup_callbacks(self):
        """Configurar callbacks del componente"""
        
        @self.app.callback(
            Output('file-tabs-content', 'children'),
            Input('file-tabs', 'active_tab')
        )
        def update_tab_content(active_tab):
            if active_tab == "explorer":
                return self.get_explorer_content()
            elif active_tab == "projects":
                return self.get_projects_content()
            elif active_tab == "process":
                return self.get_process_content()
            return html.Div()
        
        @self.app.callback(
            [Output('file-list-container', 'children'),
             Output('current-path', 'value'),
             Output('current-directory-store', 'data')],
            [Input('home-btn', 'n_clicks'),
             Input('parent-btn', 'n_clicks'),
             Input('refresh-btn', 'n_clicks'),
             Input({'type': 'file-item', 'path': ALL, 'action': ALL}, 'n_clicks')],
            [State('current-directory-store', 'data'),
             State('selected-files-store', 'data')]
        )
        def update_file_list(home_clicks, parent_clicks, refresh_clicks, file_clicks,
                           current_dir, selected_files):
            """Actualizar lista de archivos"""
            ctx = dash.callback_context
            
            new_dir = current_dir
            
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id']
                
                if 'home-btn' in button_id:
                    new_dir = os.path.expanduser("~")
                elif 'parent-btn' in button_id:
                    new_dir = os.path.dirname(current_dir)
                elif 'file-item' in button_id:
                    # Extraer información del botón clickeado
                    import json
                    btn_info = json.loads(button_id.split('.')[0])
                    if btn_info.get('action') in ['navigate', 'select'] and os.path.isdir(btn_info['path']):
                        new_dir = btn_info['path']
            
            # Actualizar directorio actual
            self.current_directory = new_dir
            
            # Obtener contenido del directorio
            items = self.get_directory_contents(new_dir)
            file_list = self.create_file_list_items(items, selected_files or [])
            
            return file_list, new_dir, new_dir