"""
Módulo para conversiones de coordenadas YOLO
"""


class CoordinateConverter:
    """Clase para convertir entre coordenadas YOLO y píxeles"""
    
    @staticmethod
    def yolo_to_pixel(annotation, img_width, img_height):
        """Convertir coordenadas YOLO normalizadas a píxeles"""
        x_center = annotation['x_center'] * img_width
        y_center = annotation['y_center'] * img_height
        width = annotation['width'] * img_width
        height = annotation['height'] * img_height
        
        x_min = max(0, x_center - width / 2)
        y_min = max(0, y_center - height / 2)
        x_max = min(img_width, x_center + width / 2)
        y_max = min(img_height, y_center + height / 2)
        
        return x_min, y_min, x_max, y_max
    
    @staticmethod
    def pixel_to_yolo(x_min, y_min, x_max, y_max, img_width, img_height):
        """Convertir coordenadas de píxeles a formato YOLO normalizado"""
        # Asegurar que las coordenadas están dentro de los límites
        x_min = max(0, min(x_min, img_width))
        y_min = max(0, min(y_min, img_height))
        x_max = max(0, min(x_max, img_width))
        y_max = max(0, min(y_max, img_height))
        
        # Asegurar que x_max > x_min y y_max > y_min
        if x_max <= x_min:
            x_max = x_min + 1
        if y_max <= y_min:
            y_max = y_min + 1
        
        x_center = ((x_min + x_max) / 2) / img_width
        y_center = ((y_min + y_max) / 2) / img_height
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height
        
        # Asegurar que los valores están normalizados
        x_center = max(0, min(1, x_center))
        y_center = max(0, min(1, y_center))
        width = max(0, min(1, width))
        height = max(0, min(1, height))
        
        return x_center, y_center, width, height
    
    @staticmethod
    def validate_pixel_coords(x_min, y_min, x_max, y_max, min_size=5):
        """Validar que las coordenadas de píxeles sean válidas"""
        return (x_max - x_min) >= min_size and (y_max - y_min) >= min_size
