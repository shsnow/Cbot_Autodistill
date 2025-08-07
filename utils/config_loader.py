"""
Módulo para cargar configuración desde archivos YAML
"""
import os
import yaml


class ConfigLoader:
    """Clase para cargar configuración desde archivos YAML"""
    
    def __init__(self, config_path="classes.yaml"):
        self.config_path = config_path
        self.config_data = None
        self._load_config()
    
    def _load_config(self):
        """Cargar datos de configuración desde el archivo YAML"""
        if not os.path.exists(self.config_path):
            print(f"⚠️ Archivo YAML no encontrado: {self.config_path}")
            self.config_data = None
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file)
            print(f"✅ Configuración cargada desde: {self.config_path}")
        except Exception as e:
            print(f"❌ Error cargando configuración: {str(e)}")
            self.config_data = None
    
    def get_classes(self):
        """Obtener lista de clases ordenada por índice"""
        if not self.config_data or 'names' not in self.config_data:
            print("⚠️ No se encontró la clave 'names' en el archivo YAML")
            print("🔄 Usando clases por defecto: ['vehículo']")
            return ["vehículo"]
        
        try:
            names_dict = self.config_data['names']
            max_index = max(names_dict.keys()) if names_dict else 0
            classes_list = [''] * (max_index + 1)
            
            for index, name in names_dict.items():
                classes_list[index] = name
            
            print(f"✅ Clases cargadas: {classes_list}")
            return classes_list
        except Exception as e:
            print(f"❌ Error procesando clases: {str(e)}")
            print("🔄 Usando clases por defecto: ['vehículo']")
            return ["vehículo"]
    
    def get_colors(self, num_classes):
        """Obtener colores personalizados para las clases"""
        default_colors = ['#00d4aa', '#ff6b6b', '#4ecdc4', '#45b7d1', 
                         '#feca57', '#ff9ff3', '#54a0ff', '#9c88ff']
        
        if not self.config_data or 'colors' not in self.config_data:
            return default_colors[:num_classes] if num_classes <= len(default_colors) else default_colors
        
        try:
            yaml_colors = []
            for rgb in self.config_data['colors']:
                if len(rgb) == 3:
                    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    yaml_colors.append(hex_color)
                else:
                    yaml_colors.append(default_colors[len(yaml_colors) % len(default_colors)])
            
            # Completar con colores por defecto si hay más clases que colores
            while len(yaml_colors) < num_classes:
                yaml_colors.append(default_colors[len(yaml_colors) % len(default_colors)])
            
            return yaml_colors
        except Exception as e:
            print(f"⚠️ Error cargando colores: {str(e)}")
            return default_colors[:num_classes] if num_classes <= len(default_colors) else default_colors
