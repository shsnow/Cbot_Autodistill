"""
Módulo para generar figuras de Plotly con anotaciones
"""
import base64
import os
from PIL import Image
import plotly.graph_objects as go
from .coordinate_converter import CoordinateConverter


class FigureGenerator:
    """Clase para generar figuras de Plotly con imágenes y anotaciones"""
    
    def __init__(self, images_path, class_colors):
        self.images_path = images_path
        self.class_colors = class_colors
        self.converter = CoordinateConverter()
    
    def get_image_as_base64(self, image_path):
        """Convertir imagen a base64 para mostrar en Dash"""
        with open(image_path, "rb") as img_file:
            img_str = base64.b64encode(img_file.read()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    
    def create_figure_with_annotations(self, image_filename, annotations, opacity=0.3, 
                                     show_ids=True, show_coords=False, selected_id=None):
        """Crear figura de Plotly con imagen y anotaciones"""
        image_path = os.path.join(self.images_path, image_filename)
        
        if not os.path.exists(image_path):
            # Crear figura vacía si la imagen no existe
            fig = go.Figure()
            fig.update_layout(title="❌ Imagen no encontrada")
            return fig, {'width': 800, 'height': 600}
        
        # Cargar imagen
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
        except Exception as e:
            fig = go.Figure()
            fig.update_layout(title=f"❌ Error cargando imagen: {str(e)}")
            return fig, {'width': 800, 'height': 600}
        
        # Crear figura
        fig = go.Figure()
        
        # Convertir imagen a base64 y agregar como fondo
        img_base64 = self.get_image_as_base64(image_path)
        
        fig.add_layout_image(
            dict(
                source=img_base64,
                xref="x",
                yref="y",
                x=0,
                y=img_height,
                sizex=img_width,
                sizey=img_height,
                sizing="stretch",
                opacity=1,
                layer="below"
            )
        )
        
        # Agregar bounding boxes como shapes
        shapes = self._create_shapes(annotations, img_width, img_height, opacity, selected_id)
        
        # Agregar etiquetas de texto
        self._add_text_annotations(fig, annotations, img_width, img_height, 
                                 show_ids, show_coords)
        
        # Configurar layout
        self._configure_layout(fig, image_filename, img_width, img_height, shapes)
        
        return fig, {'width': img_width, 'height': img_height}
    
    def _create_shapes(self, annotations, img_width, img_height, opacity, selected_id=None):
        """Crear shapes para las anotaciones"""
        shapes = []
        
        for ann in annotations:
            x_min, y_min, x_max, y_max = self.converter.yolo_to_pixel(ann, img_width, img_height)
            color = self.class_colors[ann['class_id'] % len(self.class_colors)]
            
            # Convertir coordenadas Y (Plotly usa coordenadas invertidas)
            y_min_plot = img_height - y_max
            y_max_plot = img_height - y_min
            
            # Convertir color hex a RGB para el fillcolor con transparencia
            color_rgb = [int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)]
            fill_color = f"rgba({color_rgb[0]},{color_rgb[1]},{color_rgb[2]},{opacity})"
            
            # Estilos especiales para la anotación seleccionada
            if selected_id is not None and ann['id'] == selected_id:
                line_width = 5  # Más grosor
                line_color = "#ffff00"  # Amarillo brillante
                fill_opacity = min(opacity + 0.3, 1.0)  # Más opacidad
                fill_color = f"rgba(255,255,0,{fill_opacity})"  # Amarillo semi-transparente
            else:
                line_width = 3
                line_color = color
            
            shape = dict(
                type="rect",
                x0=x_min, y0=y_min_plot,
                x1=x_max, y1=y_max_plot,
                line=dict(color=line_color, width=line_width),
                fillcolor=fill_color,
                editable=True,
                name=f"bbox_{ann['id']}",
                xref="x",
                yref="y",
                layer="above"
            )
            shapes.append(shape)
        
        return shapes
    
    def _add_text_annotations(self, fig, annotations, img_width, img_height, 
                            show_ids, show_coords):
        """Agregar etiquetas de texto a la figura"""
        for ann in annotations:
            if show_ids or show_coords:
                x_min, y_min, x_max, y_max = self.converter.yolo_to_pixel(ann, img_width, img_height)
                color = self.class_colors[ann['class_id'] % len(self.class_colors)]
                
                # Convertir coordenadas Y
                y_max_plot = img_height - y_min
                
                label_parts = []
                if show_ids:
                    label_parts.append(f"ID:{ann['id']}")
                label_parts.append(ann['class_name'])
                if show_coords:
                    label_parts.append(f"({ann['x_center']:.3f},{ann['y_center']:.3f})")
                
                label_text = " | ".join(label_parts)
                
                fig.add_annotation(
                    x=x_min,
                    y=y_max_plot,
                    text=label_text,
                    showarrow=False,
                    bgcolor=color,
                    bordercolor=color,
                    borderwidth=2,
                    font=dict(color="white", size=11, family="Arial Black"),
                    xanchor="left",
                    yanchor="bottom",
                    opacity=0.9
                )
    
    def _configure_layout(self, fig, image_filename, img_width, img_height, shapes):
        """Configurar el layout de la figura"""
        # Configurar ejes
        fig.update_xaxes(
            range=[0, img_width],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            fixedrange=True
        )
        
        fig.update_yaxes(
            range=[0, img_height],
            showgrid=False,
            showticklabels=False,
            zeroline=False,
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True
        )
        
        fig.update_layout(
            title=dict(
                text=f"📸 {image_filename} ({img_width}×{img_height}) - ✏️ Dibuja para crear • Arrastra cajas para mover/redimensionar",
                font=dict(size=16, color="#00d4aa", family="Arial Black")
            ),
            showlegend=False,
            margin=dict(l=0, r=0, t=60, b=0),
            dragmode="drawrect",
            selectdirection="d",
            newshape=dict(
                line=dict(color="#00d4aa", width=3),
                fillcolor="rgba(0,212,170,0.2)"
            ),
            plot_bgcolor='#1a1a1a',
            paper_bgcolor='#1a1a1a',
            shapes=shapes,
            font=dict(color="#adb5bd")
        )
