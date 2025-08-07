"""
Herramienta de Corrección de Etiquetado con Gradio - Alternativa Simple
Interfaz más sencilla para editar anotaciones YOLO
"""

import gradio as gr
import cv2
import numpy as np
import os
import json
from PIL import Image, ImageDraw, ImageFont
import tempfile
import base64
import io

class GradioAnnotationTool:
    def __init__(self, dataset_path="dataset_cruce_3"):
        self.dataset_path = dataset_path
        self.images_path = os.path.join(dataset_path, "train", "images")
        self.labels_path = os.path.join(dataset_path, "train", "labels")
        self.classes = ["vehículo"]  # Basado en tu ontología
        
        # Verificar que los directorios existen
        if not os.path.exists(self.images_path):
            raise FileNotFoundError(f"Directorio de imágenes no encontrado: {self.images_path}")
        
        self.image_files = sorted([f for f in os.listdir(self.images_path) 
                                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        if not self.image_files:
            raise FileNotFoundError(f"No se encontraron imágenes en: {self.images_path}")
        
        self.current_image_index = 0
        self.current_annotations = []
        
        print(f"🔧 Herramienta de Anotación Gradio iniciada")
        print(f"📁 Dataset: {self.dataset_path}")
        print(f"🖼️ Imágenes encontradas: {len(self.image_files)}")
    
    def load_image_annotations(self, image_filename):
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
        label_filename = os.path.splitext(image_filename)[0] + '.txt'
        label_path = os.path.join(self.labels_path, label_filename)
        
        if not annotations:
            if os.path.exists(label_path):
                os.remove(label_path)
            return
        
        with open(label_path, 'w') as f:
            for ann in annotations:
                line = f"{ann['class_id']} {ann['x_center']:.6f} {ann['y_center']:.6f} {ann['width']:.6f} {ann['height']:.6f}\n"
                f.write(line)
    
    def yolo_to_pixel_coords(self, annotation, img_width, img_height):
        """Convertir coordenadas YOLO normalizadas a píxeles"""
        x_center = annotation['x_center'] * img_width
        y_center = annotation['y_center'] * img_height
        width = annotation['width'] * img_width
        height = annotation['height'] * img_height
        
        x_min = max(0, x_center - width / 2)
        y_min = max(0, y_center - height / 2)
        x_max = min(img_width, x_center + width / 2)
        y_max = min(img_height, y_center + height / 2)
        
        return int(x_min), int(y_min), int(x_max), int(y_max)
    
    def pixel_to_yolo_coords(self, x_min, y_min, x_max, y_max, img_width, img_height):
        """Convertir coordenadas de píxeles a formato YOLO normalizado"""
        x_center = ((x_min + x_max) / 2) / img_width
        y_center = ((y_min + y_max) / 2) / img_height
        width = (x_max - x_min) / img_width
        height = (y_max - y_min) / img_height
        
        return max(0, min(1, x_center)), max(0, min(1, y_center)), max(0, min(1, width)), max(0, min(1, height))
    
    def draw_annotations_on_image(self, image_path, annotations):
        """Dibujar anotaciones en la imagen"""
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # Colores para las clases
        colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF']
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        for ann in annotations:
            x_min, y_min, x_max, y_max = self.yolo_to_pixel_coords(ann, img.width, img.height)
            color = colors[ann['class_id'] % len(colors)]
            
            # Dibujar rectángulo
            draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=3)
            
            # Dibujar etiqueta
            label = f"{ann['class_name']} (ID:{ann['id']})"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Fondo para el texto
            draw.rectangle([x_min, y_min - text_height - 4, x_min + text_width + 4, y_min], fill=color)
            draw.text((x_min + 2, y_min - text_height - 2), label, fill='white', font=font)
        
        return img
    
    def load_current_image(self):
        """Cargar imagen actual con anotaciones"""
        if not self.image_files:
            return None, "No hay imágenes disponibles", ""
        
        current_image = self.image_files[self.current_image_index]
        image_path = os.path.join(self.images_path, current_image)
        
        # Cargar anotaciones
        self.current_annotations = self.load_image_annotations(current_image)
        
        # Crear imagen con anotaciones
        img_with_annotations = self.draw_annotations_on_image(image_path, self.current_annotations)
        
        # Información
        info = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
        
        # Lista de anotaciones
        annotations_text = self.format_annotations_list()
        
        return img_with_annotations, info, annotations_text
    
    def format_annotations_list(self):
        """Formatear lista de anotaciones como texto"""
        if not self.current_annotations:
            return "📭 No hay anotaciones en esta imagen"
        
        text = f"🏷️ Anotaciones ({len(self.current_annotations)}):\n\n"
        for ann in self.current_annotations:
            text += f"ID: {ann['id']} | Clase: {ann['class_name']}\n"
            text += f"Centro: ({ann['x_center']:.3f}, {ann['y_center']:.3f})\n"
            text += f"Tamaño: {ann['width']:.3f} × {ann['height']:.3f}\n"
            text += "-" * 40 + "\n"
        
        return text
    
    def navigate_next(self):
        """Ir a la siguiente imagen"""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
        return self.load_current_image()
    
    def navigate_prev(self):
        """Ir a la imagen anterior"""
        if self.current_image_index > 0:
            self.current_image_index -= 1
        return self.load_current_image()
    
    def navigate_first(self):
        """Ir a la primera imagen"""
        self.current_image_index = 0
        return self.load_current_image()
    
    def navigate_last(self):
        """Ir a la última imagen"""
        self.current_image_index = len(self.image_files) - 1
        return self.load_current_image()
    
    def add_annotation(self, x_min, y_min, x_max, y_max, class_id):
        """Agregar nueva anotación"""
        if not self.image_files:
            return self.load_current_image()[0], self.load_current_image()[1], "❌ No hay imagen cargada", "❌ Error"
        
        current_image = self.image_files[self.current_image_index]
        image_path = os.path.join(self.images_path, current_image)
        img = Image.open(image_path)
        
        try:
            # Validar coordenadas
            x_min, y_min, x_max, y_max = int(x_min), int(y_min), int(x_max), int(y_max)
            
            if x_min >= x_max or y_min >= y_max:
                return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], "❌ Coordenadas inválidas"
            
            # Convertir a YOLO
            x_center, y_center, width, height = self.pixel_to_yolo_coords(
                x_min, y_min, x_max, y_max, img.width, img.height
            )
            
            # Crear nueva anotación
            new_annotation = {
                'id': len(self.current_annotations),
                'class_id': class_id,
                'class_name': self.classes[class_id],
                'x_center': x_center,
                'y_center': y_center,
                'width': width,
                'height': height
            }
            
            self.current_annotations.append(new_annotation)
            
            # Recargar imagen
            img_with_annotations = self.draw_annotations_on_image(image_path, self.current_annotations)
            info = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
            annotations_text = self.format_annotations_list()
            
            return img_with_annotations, info, annotations_text, "✅ Anotación agregada"
            
        except Exception as e:
            return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], f"❌ Error: {str(e)}"
    
    def delete_annotation(self, ann_id):
        """Eliminar anotación por ID"""
        try:
            ann_id = int(ann_id)
            original_count = len(self.current_annotations)
            
            # Filtrar anotaciones
            self.current_annotations = [ann for ann in self.current_annotations if ann['id'] != ann_id]
            
            # Reindexar IDs
            for i, ann in enumerate(self.current_annotations):
                ann['id'] = i
            
            if len(self.current_annotations) < original_count:
                # Recargar imagen
                current_image = self.image_files[self.current_image_index]
                image_path = os.path.join(self.images_path, current_image)
                img_with_annotations = self.draw_annotations_on_image(image_path, self.current_annotations)
                info = f"Imagen {self.current_image_index + 1} de {len(self.image_files)}: {current_image}"
                annotations_text = self.format_annotations_list()
                
                return img_with_annotations, info, annotations_text, f"✅ Anotación {ann_id} eliminada"
            else:
                return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], "❌ ID no encontrado"
                
        except Exception as e:
            return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], f"❌ Error: {str(e)}"
    
    def save_current_annotations(self):
        """Guardar anotaciones de la imagen actual"""
        try:
            current_image = self.image_files[self.current_image_index]
            self.save_annotations(current_image, self.current_annotations)
            return "✅ Anotaciones guardadas correctamente"
        except Exception as e:
            return f"❌ Error guardando: {str(e)}"
    
    def delete_current_frame(self):
        """Eliminar frame actual"""
        try:
            current_image = self.image_files[self.current_image_index]
            
            # Eliminar archivos
            img_path = os.path.join(self.images_path, current_image)
            label_path = os.path.join(self.labels_path, os.path.splitext(current_image)[0] + '.txt')
            
            if os.path.exists(img_path):
                os.remove(img_path)
            if os.path.exists(label_path):
                os.remove(label_path)
            
            # Actualizar lista de archivos
            self.image_files = sorted([f for f in os.listdir(self.images_path) 
                                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            
            # Ajustar índice
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = max(0, len(self.image_files) - 1)
            
            if self.image_files:
                return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], "🗑️ Frame eliminado"
            else:
                return None, "No hay más imágenes", "", "🗑️ Última imagen eliminada"
                
        except Exception as e:
            return self.load_current_image()[0], self.load_current_image()[1], self.load_current_image()[2], f"❌ Error eliminando: {str(e)}"
    
    def create_interface(self):
        """Crear interfaz de Gradio"""
        with gr.Blocks(title="🔧 Herramienta de Corrección de Etiquetado", theme=gr.themes.Soft()) as interface:
            gr.HTML("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1>🔧 Herramienta de Corrección de Etiquetado</h1>
                <p>Edita anotaciones YOLO de manera sencilla</p>
            </div>
            """)
            
            with gr.Row():
                with gr.Column(scale=3):
                    # Imagen principal
                    image_display = gr.Image(
                        label="📸 Imagen con Anotaciones",
                        type="pil",
                        height=500
                    )
                    
                    # Información de la imagen
                    image_info = gr.Textbox(
                        label="ℹ️ Información",
                        interactive=False
                    )
                
                with gr.Column(scale=1):
                    # Controles de navegación
                    gr.HTML("<h3>📂 Navegación</h3>")
                    with gr.Row():
                        first_btn = gr.Button("◀◀ Primero", size="sm")
                        prev_btn = gr.Button("◀ Anterior", size="sm")
                    with gr.Row():
                        next_btn = gr.Button("Siguiente ▶", size="sm")
                        last_btn = gr.Button("Último ▶▶", size="sm")
                    
                    gr.HTML("<hr>")
                    
                    # Agregar anotación
                    gr.HTML("<h3>➕ Agregar Anotación</h3>")
                    with gr.Row():
                        x_min = gr.Number(label="X Min", value=0)
                        y_min = gr.Number(label="Y Min", value=0)
                    with gr.Row():
                        x_max = gr.Number(label="X Max", value=100)
                        y_max = gr.Number(label="Y Max", value=100)
                    
                    class_selector = gr.Dropdown(
                        choices=[(cls, i) for i, cls in enumerate(self.classes)],
                        value=0,
                        label="Clase"
                    )
                    add_btn = gr.Button("➕ Agregar Caja", variant="primary")
                    
                    gr.HTML("<hr>")
                    
                    # Eliminar anotación
                    gr.HTML("<h3>🗑️ Eliminar Anotación</h3>")
                    delete_id = gr.Number(label="ID a Eliminar", value=0)
                    delete_ann_btn = gr.Button("🗑️ Eliminar", variant="secondary")
                    
                    gr.HTML("<hr>")
                    
                    # Acciones
                    gr.HTML("<h3>💾 Acciones</h3>")
                    save_btn = gr.Button("💾 Guardar", variant="primary")
                    delete_frame_btn = gr.Button("🗑️ Eliminar Frame", variant="stop")
                    
                    # Estado/mensajes
                    status_message = gr.Textbox(
                        label="📢 Estado",
                        interactive=False
                    )
            
            # Lista de anotaciones
            annotations_list = gr.Textbox(
                label="🏷️ Lista de Anotaciones",
                lines=8,
                interactive=False
            )
            
            # Configurar eventos
            interface.load(self.load_current_image, outputs=[image_display, image_info, annotations_list])
            
            next_btn.click(self.navigate_next, outputs=[image_display, image_info, annotations_list])
            prev_btn.click(self.navigate_prev, outputs=[image_display, image_info, annotations_list])
            first_btn.click(self.navigate_first, outputs=[image_display, image_info, annotations_list])
            last_btn.click(self.navigate_last, outputs=[image_display, image_info, annotations_list])
            
            add_btn.click(
                self.add_annotation,
                inputs=[x_min, y_min, x_max, y_max, class_selector],
                outputs=[image_display, image_info, annotations_list, status_message]
            )
            
            delete_ann_btn.click(
                self.delete_annotation,
                inputs=[delete_id],
                outputs=[image_display, image_info, annotations_list, status_message]
            )
            
            save_btn.click(self.save_current_annotations, outputs=[status_message])
            
            delete_frame_btn.click(
                self.delete_current_frame,
                outputs=[image_display, image_info, annotations_list, status_message]
            )
        
        return interface
    
    def run(self, share=False, debug=True):
        """Ejecutar la aplicación Gradio"""
        print("🚀 Iniciando Herramienta de Anotación con Gradio...")
        interface = self.create_interface()
        interface.launch(share=share, debug=debug, inbrowser=True)

if __name__ == "__main__":
    try:
        tool = GradioAnnotationTool()
        tool.run(share=False, debug=False)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Asegúrate de que el directorio dataset_cruce_3 existe y contiene imágenes")
