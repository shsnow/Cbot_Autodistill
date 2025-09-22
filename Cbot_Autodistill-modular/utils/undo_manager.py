"""
Módulo para el sistema de deshacer (undo)
"""


class UndoManager:
    """Clase para manejar el sistema de deshacer acciones"""
    
    def __init__(self, max_steps=20):
        self.undo_stack = []
        self.max_steps = max_steps
    
    def push_state(self, image_filename, annotations):
        """Agregar estado al stack de undo"""
        state = {
            'image_filename': image_filename,
            'annotations': [ann.copy() for ann in annotations]  # Deep copy
        }
        
        self.undo_stack.append(state)
        
        # Limitar el tamaño del stack
        if len(self.undo_stack) > self.max_steps:
            self.undo_stack.pop(0)
    
    def pop_state(self):
        """Recuperar último estado del stack de undo"""
        if self.undo_stack:
            return self.undo_stack.pop()
        return None
    
    def can_undo(self):
        """Verificar si se puede deshacer"""
        return len(self.undo_stack) > 0
    
    def get_undo_count(self):
        """Obtener número de acciones que se pueden deshacer"""
        return len(self.undo_stack)
    
    def clear(self):
        """Limpiar el stack de undo"""
        self.undo_stack.clear()
    
    def get_last_state_for_image(self, image_filename):
        """Obtener el último estado para una imagen específica"""
        for state in reversed(self.undo_stack):
            if state['image_filename'] == image_filename:
                return state
        return None
