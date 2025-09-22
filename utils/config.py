"""
Configuración global de AutoDistill Suite
"""

import os
from pathlib import Path

class Config:
    # Directorios base
    BASE_DIR = Path(__file__).parent.parent
    STATIC_DIR = BASE_DIR / "static"
    TEMP_DIR = BASE_DIR / "temp"
    PROJECTS_DIR = BASE_DIR / "projects"
    
    # Archivos de configuración
    PROJECTS_FILE = BASE_DIR / "projects.json"
    SETTINGS_FILE = BASE_DIR / "settings.json"
    
    # Formatos soportados
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
    
    # Configuración de AutoDistill
    DEFAULT_CONFIDENCE = 0.5
    DEFAULT_CLASSES = ["vehículo"]
    
    # Configuración de extracción de frames
    DEFAULT_FRAME_INTERVAL = 30
    DEFAULT_IMAGE_QUALITY = 95
    
    # Configuración de datasets
    DEFAULT_TRAIN_SPLIT = 0.7
    DEFAULT_VAL_SPLIT = 0.2
    DEFAULT_TEST_SPLIT = 0.1
    
    # Modelos disponibles para AutoDistill
    AUTODISTILL_MODELS = {
        "GroundedSAM": {
            "package": "autodistill-grounded-sam",
            "class": "GroundedSAM",
            "requires_cuda": True,
            "memory_usage": "High",
            "description": "Modelo más preciso pero requiere más recursos"
        },
        "CLIP": {
            "package": "autodistill-clip", 
            "class": "CLIP",
            "requires_cuda": False,
            "memory_usage": "Low",
            "description": "Modelo rápido y eficiente para clasificación"
        },
        "OWL-ViT": {
            "package": "autodistill-owl-vit",
            "class": "OWLViT", 
            "requires_cuda": True,
            "memory_usage": "Medium",
            "description": "Buen balance entre velocidad y precisión"
        }
    }
    
    # Configuración de UI
    UI_THEME = "CYBORG"  # Tema oscuro de Bootstrap
    PRIMARY_COLOR = "#00d4aa"
    SECONDARY_COLOR = "#20c997"
    
    @classmethod
    def ensure_directories(cls):
        """Crear directorios necesarios si no existen"""
        for dir_path in [cls.STATIC_DIR, cls.TEMP_DIR, cls.PROJECTS_DIR]:
            dir_path.mkdir(exist_ok=True)
    
    @classmethod
    def get_temp_path(cls, filename):
        """Obtener ruta temporal para un archivo"""
        cls.ensure_directories()
        return cls.TEMP_DIR / filename
    
    @classmethod
    def is_image_file(cls, filename):
        """Verificar si un archivo es una imagen soportada"""
        return any(filename.lower().endswith(ext) for ext in cls.SUPPORTED_IMAGE_FORMATS)
    
    @classmethod
    def is_video_file(cls, filename):
        """Verificar si un archivo es un video soportado"""
        return any(filename.lower().endswith(ext) for ext in cls.SUPPORTED_VIDEO_FORMATS)