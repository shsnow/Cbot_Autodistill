"""
Módulo para manejo de anotaciones YOLO
"""
import os


class AnnotationManager:
    """Clase para manejar las operaciones con anotaciones YOLO"""
    
    def __init__(self, labels_path, classes):
        self.labels_path = labels_path
        self.classes = classes
    
    def load_annotations(self, image_filename):
        """Cargar anotaciones para una imagen específica"""
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        annotations = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line_idx, line in enumerate(f.readlines()):
                    line = line.strip()
                    if line:
                        try:
                            parts = line.split()
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            # Validar que los valores estén en rango válido
                            if (0 <= x_center <= 1 and 0 <= y_center <= 1 and 
                                0 <= width <= 1 and 0 <= height <= 1 and
                                class_id < len(self.classes)):
                                
                                annotations.append({
                                    'id': line_idx,
                                    'class_id': class_id,
                                    'class_name': self.classes[class_id],
                                    'x_center': x_center,
                                    'y_center': y_center,
                                    'width': width,
                                    'height': height
                                })
                        except (ValueError, IndexError) as e:
                            print(f"Error leyendo línea {line_idx + 1} en {label_filename}: {e}")
                            continue
        
        return annotations
    
    def save_annotations(self, image_filename, annotations):
        """Guardar anotaciones en formato YOLO"""
        print(f"DEBUG: Guardando {len(annotations)} anotaciones para {image_filename}")
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        if not annotations:
            # Si no hay anotaciones, eliminar archivo si existe
            if os.path.exists(label_path):
                os.remove(label_path)
                print(f"DEBUG: Archivo eliminado: {label_path}")
            return
        
        try:
            with open(label_path, 'w') as f:
                for ann in annotations:
                    line = f"{ann['class_id']} {ann['x_center']:.6f} {ann['y_center']:.6f} {ann['width']:.6f} {ann['height']:.6f}\n"
                    f.write(line)
            print(f"DEBUG: Archivo guardado exitosamente: {label_path}")
            
            # Verificar que se guardó correctamente
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    lines = f.readlines()
                    print(f"DEBUG: Archivo tiene {len(lines)} líneas guardadas")
        except Exception as e:
            print(f"ERROR: Fallo al guardar {label_path}: {str(e)}")
            raise
    
    def validate_annotation(self, annotation):
        """Validar que una anotación tenga valores correctos"""
        required_keys = ['class_id', 'x_center', 'y_center', 'width', 'height']
        
        if not all(key in annotation for key in required_keys):
            return False
        
        # Validar rangos
        if not (0 <= annotation['x_center'] <= 1 and 
                0 <= annotation['y_center'] <= 1 and
                0 <= annotation['width'] <= 1 and 
                0 <= annotation['height'] <= 1):
            return False
        
        # Validar class_id
        if annotation['class_id'] < 0 or annotation['class_id'] >= len(self.classes):
            return False
        
        return True
