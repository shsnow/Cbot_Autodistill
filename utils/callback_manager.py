"""
Módulo para los callbacks de Dash
"""
import json
from dash import ctx, no_update
from .coordinate_converter import CoordinateConverter


class CallbackManager:
    """Clase para manejar los callbacks de Dash"""
    
    def __init__(self, annotation_manager, undo_manager, figure_generator, classes):
        self.annotation_manager = annotation_manager
        self.undo_manager = undo_manager
        self.figure_generator = figure_generator
        self.classes = classes
        self.converter = CoordinateConverter()
    
    def handle_shape_interaction(self, relayout_data, annotations, img_dims, image_data, 
                               selected_class, opacity, display_options):
        """Manejar interacción con formas - creación y edición"""
        if not relayout_data or not img_dims or not image_data:
            return annotations or [], no_update, False, ""

        annotations = annotations or []
        
        print(f"DEBUG: relayout_data keys: {relayout_data.keys()}")
        
        # Detectar nueva forma dibujada
        if 'shapes' in relayout_data and relayout_data['shapes']:
            shapes = relayout_data['shapes']
            print(f"DEBUG: Shapes count: {len(shapes)}, Annotations count: {len(annotations)}")
            
            # Si hay más shapes que anotaciones actuales, es una nueva forma
            if len(shapes) > len(annotations):
                print("DEBUG: Detectada nueva forma")
                return self._handle_new_shape(shapes[-1], annotations, img_dims, image_data, 
                                            selected_class, opacity, display_options)
            
            # Si hay igual número de shapes, podría ser edición
            elif len(shapes) == len(annotations) and shapes:
                print("DEBUG: Detectada posible edición")
                return self._handle_shape_edit(shapes, annotations, img_dims, image_data, 
                                             opacity, display_options)
        
        # Manejar edición de shape individual por coordenada
        shape_coord_changed = False
        shape_index = None
        shape_updates = {}
        
        for key in relayout_data:
            if key.startswith('shapes[') and any(key.endswith(coord) for coord in ['].x0', '].x1', '].y0', '].y1']):
                print(f"DEBUG: Detectada edición individual de forma: {key} = {relayout_data[key]}")
                shape_coord_changed = True
                
                # Extraer índice de la shape y la coordenada
                try:
                    parts = key.replace('shapes[', '').replace(']', '').split('.')
                    shape_idx = int(parts[0])
                    coord_name = parts[1]
                    shape_index = shape_idx
                    
                    if shape_idx not in shape_updates:
                        shape_updates[shape_idx] = {}
                    shape_updates[shape_idx][coord_name] = relayout_data[key]
                    
                    print(f"DEBUG: Shape index: {shape_idx}, coord: {coord_name}, value: {relayout_data[key]}")
                except Exception as e:
                    print(f"DEBUG: Error extrayendo índice: {e}")
        
        # Si tenemos cambios de coordenadas individuales, reconstruir las shapes
        if shape_coord_changed and shape_updates:
            print(f"DEBUG: RECONSTRUYENDO shapes con cambios individuales")
            print(f"DEBUG: Shape updates: {shape_updates}")
            
            # Necesitamos reconstruir las shapes completas a partir de las anotaciones actuales
            # y aplicar los cambios individuales
            reconstructed_shapes = []
            
            for i, ann in enumerate(annotations):
                # Convertir anotación actual a coordenadas de shape
                x_center = ann['x_center'] * img_dims['width']
                y_center = ann['y_center'] * img_dims['height']
                width = ann['width'] * img_dims['width']
                height = ann['height'] * img_dims['height']
                
                # Calcular coordenadas de la shape (esquinas)
                x0 = x_center - width / 2
                x1 = x_center + width / 2
                y0 = img_dims['height'] - (y_center + height / 2)  # Plotly Y invertido
                y1 = img_dims['height'] - (y_center - height / 2)  # Plotly Y invertido
                
                shape = {
                    'x0': x0,
                    'x1': x1, 
                    'y0': y0,
                    'y1': y1,
                    'type': 'rect',
                    'line': {'color': 'rgba(0,212,170,1)', 'width': 2}
                }
                
                # Si esta shape tiene cambios, aplicarlos
                if i in shape_updates:
                    updates = shape_updates[i]
                    print(f"DEBUG: Aplicando cambios a shape {i}: {updates}")
                    for coord, value in updates.items():
                        shape[coord] = value
                
                reconstructed_shapes.append(shape)
            
            print(f"DEBUG: Shapes reconstruidas: {len(reconstructed_shapes)}")
            
            # Ahora procesar con las shapes reconstruidas
            return self._handle_shape_edit(reconstructed_shapes, annotations, img_dims, image_data, 
                                         opacity, display_options)
        
        # No hacer nada si no hay cambios relevantes
        return annotations, no_update, False, ""
    
    def _handle_new_shape(self, new_shape, annotations, img_dims, image_data, 
                         selected_class, opacity, display_options):
        """Manejar creación de nueva forma"""
        try:
            print(f"DEBUG: Creando nueva shape con datos: {new_shape}")
            print(f"DEBUG: Annotations actuales: {len(annotations)}")
            print(f"DEBUG: img_dims: {img_dims}")
            print(f"DEBUG: image_data: {image_data}")
            print(f"DEBUG: selected_class: {selected_class}, type: {type(selected_class)}")
            print(f"DEBUG: classes disponibles: {self.classes}, type: {type(self.classes)}")
            
            # Obtener coordenadas
            x0 = min(new_shape['x0'], new_shape['x1'])
            x1 = max(new_shape['x0'], new_shape['x1'])
            y0 = min(new_shape['y0'], new_shape['y1'])
            y1 = max(new_shape['y0'], new_shape['y1'])
            
            print(f"DEBUG: Coordenadas extraídas: x0={x0}, y0={y0}, x1={x1}, y1={y1}")
            
            # Convertir coordenadas Y (Plotly usa coordenadas invertidas)
            y0_img = img_dims['height'] - y1
            y1_img = img_dims['height'] - y0
            
            print(f"DEBUG: Coordenadas convertidas: x0={x0}, y0_img={y0_img}, x1={x1}, y1_img={y1_img}")
            
            # Validar tamaño mínimo
            if not self.converter.validate_pixel_coords(x0, y0_img, x1, y1_img, min_size=10):
                return annotations, no_update, True, "⚠️ La caja es muy pequeña (mínimo 10x10 píxeles)"
            
            # Guardar estado actual para undo ANTES de crear la nueva anotación
            self.undo_manager.push_state(image_data['filename'], annotations)
            
            # Convertir a coordenadas YOLO
            x_center, y_center, width, height = self.converter.pixel_to_yolo(
                x0, y0_img, x1, y1_img, img_dims['width'], img_dims['height']
            )
            
            print(f"DEBUG: Coordenadas YOLO: center=({x_center}, {y_center}), size=({width}, {height})")
            
            # Validar selected_class
            if not isinstance(selected_class, int):
                print(f"DEBUG: WARNING - selected_class no es int, es {type(selected_class)}: {selected_class}")
                try:
                    selected_class = int(selected_class)
                    print(f"DEBUG: Convertido a int: {selected_class}")
                except (ValueError, TypeError):
                    print(f"DEBUG: ERROR - No se puede convertir selected_class a int")
                    selected_class = 0  # Usar clase por defecto
            
            # Validar que selected_class esté en rango
            if selected_class < 0 or selected_class >= len(self.classes):
                print(f"DEBUG: WARNING - selected_class fuera de rango: {selected_class}, usando 0")
                selected_class = 0
            
            print(f"DEBUG: selected_class validado: {selected_class}")
            print(f"DEBUG: Clase seleccionada: {self.classes[selected_class]}")
            
            # Crear nueva anotación
            new_annotation = {
                'id': len(annotations),
                'class_id': selected_class,
                'class_name': self.classes[selected_class],
                'x_center': x_center,
                'y_center': y_center,
                'width': width,
                'height': height
            }
            
            print(f"DEBUG: Nueva anotación creada: {new_annotation}")
            
            new_annotations = annotations + [new_annotation]
            
            print(f"DEBUG: Total anotaciones después de añadir: {len(new_annotations)}")
            
            # Guardar automáticamente
            try:
                self.annotation_manager.save_annotations(image_data['filename'], new_annotations)
                print("DEBUG: Guardado exitoso de nueva anotación")
            except Exception as save_error:
                print(f"ERROR guardando nueva anotación: {save_error}")
                import traceback
                traceback.print_exc()
            
            # Regenerar figura
            show_ids = 'show_ids' in (display_options or ['show_ids'])
            show_coords = 'show_coords' in (display_options or [])
            
            print(f"DEBUG: Regenerando figura con {len(new_annotations)} anotaciones")
            
            fig, _ = self.figure_generator.create_figure_with_annotations(
                image_data['filename'], new_annotations, opacity, show_ids, show_coords
            )
            
            print("DEBUG: Figura regenerada exitosamente")
            
            return new_annotations, fig, True, f"✅ Nueva caja: {self.classes[selected_class]} - Guardado automático"
            
        except Exception as e:
            print(f"ERROR COMPLETO creando nueva anotación: {str(e)}")
            import traceback
            traceback.print_exc()
            return annotations, no_update, True, f"❌ Error creando caja: {str(e)}"
    
    def _handle_shape_edit(self, shapes, annotations, img_dims, image_data, opacity, display_options):
        """Manejar edición de formas existentes"""
        try:
            # Guardar estado para undo ANTES de hacer cualquier cambio
            self.undo_manager.push_state(image_data['filename'], annotations)
            
            updated_annotations = []
            changes_made = False
            
            print(f"DEBUG: Editando {len(shapes)} shapes, {len(annotations)} annotations")
            
            for i, (shape, ann) in enumerate(zip(shapes, annotations)):
                print(f"DEBUG: Procesando shape {i}: {shape}")
                
                # Obtener coordenadas de la shape editada
                x0 = min(shape['x0'], shape['x1'])
                x1 = max(shape['x0'], shape['x1'])
                y0 = min(shape['y0'], shape['y1'])
                y1 = max(shape['y0'], shape['y1'])
                
                print(f"DEBUG: Coordenadas pixel: x0={x0}, y0={y0}, x1={x1}, y1={y1}")
                
                # Convertir coordenadas Y
                y0_img = img_dims['height'] - y1
                y1_img = img_dims['height'] - y0
                
                print(f"DEBUG: Coordenadas convertidas: x0={x0}, y0_img={y0_img}, x1={x1}, y1_img={y1_img}")
                
                # Validar tamaño mínimo
                if self.converter.validate_pixel_coords(x0, y0_img, x1, y1_img, min_size=5):
                    # Convertir a YOLO
                    x_center, y_center, width, height = self.converter.pixel_to_yolo(
                        x0, y0_img, x1, y1_img, img_dims['width'], img_dims['height']
                    )
                    
                    print(f"DEBUG: Nuevas coordenadas YOLO: center=({x_center:.6f}, {y_center:.6f}), size=({width:.6f}, {height:.6f})")
                    print(f"DEBUG: Coordenadas anteriores: center=({ann['x_center']:.6f}, {ann['y_center']:.6f}), size=({ann['width']:.6f}, {ann['height']:.6f})")
                    
                    # Verificar si hubo cambios (tolerancia muy pequeña)
                    x_change = abs(ann['x_center'] - x_center)
                    y_change = abs(ann['y_center'] - y_center)
                    w_change = abs(ann['width'] - width)
                    h_change = abs(ann['height'] - height)
                    
                    print(f"DEBUG: Cambios calculados: dx={x_change:.8f}, dy={y_change:.8f}, dw={w_change:.8f}, dh={h_change:.8f}")
                    
                    if (x_change > 0.00001 or y_change > 0.00001 or w_change > 0.00001 or h_change > 0.00001):
                        changes_made = True
                        print(f"DEBUG: ¡CAMBIOS DETECTADOS en anotación {i}!")
                        print(f"  Anterior: center=({ann['x_center']:.6f}, {ann['y_center']:.6f}), size=({ann['width']:.6f}, {ann['height']:.6f})")
                        print(f"  Nuevo: center=({x_center:.6f}, {y_center:.6f}), size=({width:.6f}, {height:.6f})")
                    else:
                        print(f"DEBUG: No hay cambios significativos en anotación {i}")
                    
                    # Actualizar anotación
                    updated_ann = ann.copy()
                    updated_ann['x_center'] = x_center
                    updated_ann['y_center'] = y_center
                    updated_ann['width'] = width
                    updated_ann['height'] = height
                    updated_annotations.append(updated_ann)
                else:
                    # Mantener anotación original si es muy pequeña
                    print(f"DEBUG: Shape {i} demasiado pequeña, manteniendo original")
                    updated_annotations.append(ann)
            
            # Solo guardar si algo cambió
            if changes_made:
                print(f"DEBUG: ¡GUARDANDO CAMBIOS! para imagen {image_data['filename']}")
                
                # Guardar automáticamente
                try:
                    self.annotation_manager.save_annotations(image_data['filename'], updated_annotations)
                    print("DEBUG: ¡Guardado exitoso!")
                except Exception as save_error:
                    print(f"ERROR guardando automáticamente: {save_error}")
                
                # Regenerar figura
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                fig, _ = self.figure_generator.create_figure_with_annotations(
                    image_data['filename'], updated_annotations, opacity, show_ids, show_coords
                )
                
                return updated_annotations, fig, True, "✏️ Caja editada - Guardado automático"
            else:
                print("DEBUG: NO hay cambios que guardar")
            
        except Exception as e:
            print(f"ERROR editando anotación: {str(e)}")
            import traceback
            traceback.print_exc()
            return annotations, no_update, True, f"❌ Error editando: {str(e)}"
        
        return annotations, no_update, False, ""
    
    def handle_delete_annotation(self, delete_clicks, annotations, image_data, opacity, display_options):
        """Eliminar anotación específica"""
        if not any(delete_clicks or []) or not ctx.triggered:
            return annotations, no_update, False, ""
        
        try:
            # Guardar estado para undo ANTES de eliminar
            self.undo_manager.push_state(image_data['filename'], annotations)
            
            # Obtener el ID de la anotación a eliminar
            triggered_prop_id = ctx.triggered[0]['prop_id']
            prop_id_dict = json.loads(triggered_prop_id.split('.')[0])
            delete_id = prop_id_dict['index']
            
            # Filtrar anotaciones
            original_count = len(annotations)
            annotations = [ann for ann in annotations if ann['id'] != delete_id]
            
            # Reindexar IDs
            for i, ann in enumerate(annotations):
                ann['id'] = i
            
            if len(annotations) < original_count:
                # Regenerar figura
                show_ids = 'show_ids' in (display_options or ['show_ids'])
                show_coords = 'show_coords' in (display_options or [])
                fig, _ = self.figure_generator.create_figure_with_annotations(
                    image_data['filename'], annotations, opacity, show_ids, show_coords
                )
                
                # Guardar automáticamente
                try:
                    self.annotation_manager.save_annotations(image_data['filename'], annotations)
                except Exception as save_error:
                    print(f"Error guardando automáticamente: {save_error}")
                
                return annotations, fig, True, f"🗑️ Anotación eliminada - Guardado automático"
            
        except Exception as e:
            return annotations, no_update, True, f"❌ Error eliminando anotación: {str(e)}"
        
        return annotations, no_update, False, ""
    
    def handle_delete_last_annotation(self, delete_clicks, annotations, image_data, opacity, display_options):
        """Eliminar la última anotación (más recientemente creada)"""
        print(f"DEBUG DELETE LAST: Clicks={delete_clicks}, Annotations={len(annotations or [])}")
        
        if not delete_clicks:
            print("DEBUG DELETE LAST: No hay clicks, retornando")
            return annotations or [], no_update, False, ""
            
        if not annotations or len(annotations) == 0:
            print("DEBUG DELETE LAST: No hay anotaciones para eliminar")
            return annotations or [], no_update, True, "⚠️ No hay anotaciones para eliminar"
        
        try:
            print(f"DEBUG DELETE LAST: Eliminando última anotación (ID: {annotations[-1].get('id', 'sin-id')})")
            
            # Guardar estado para undo ANTES de eliminar
            self.undo_manager.push_state(image_data['filename'], annotations)
            
            # Eliminar la última anotación
            annotations_filtered = annotations[:-1]
            
            # Reindexar IDs
            for i, ann in enumerate(annotations_filtered):
                ann['id'] = i
            
            print(f"DEBUG DELETE LAST: Anotación eliminada exitosamente. Quedan {len(annotations_filtered)} anotaciones")
            
            # Regenerar figura
            show_ids = 'show_ids' in (display_options or ['show_ids'])
            show_coords = 'show_coords' in (display_options or [])
            fig, _ = self.figure_generator.create_figure_with_annotations(
                image_data['filename'], annotations_filtered, opacity, show_ids, show_coords
            )
            
            # Guardar automáticamente
            try:
                self.annotation_manager.save_annotations(image_data['filename'], annotations_filtered)
                print("DEBUG DELETE LAST: Guardado exitoso después de eliminar")
            except Exception as save_error:
                print(f"ERROR DELETE LAST guardando automáticamente: {save_error}")
            
            return annotations_filtered, fig, True, "🗑️ Última anotación eliminada - Guardado automático"
            
        except Exception as e:
            print(f"ERROR DELETE LAST eliminando anotación: {str(e)}")
            import traceback
            traceback.print_exc()
            return annotations or [], no_update, True, f"❌ Error eliminando anotación: {str(e)}"
    
    def handle_delete_by_id_annotation(self, delete_clicks, annotations, delete_id, image_data, opacity, display_options):
        """Eliminar anotación por ID específico"""
        print(f"DEBUG DELETE ID: Clicks={delete_clicks}, ID={delete_id}, Annotations={len(annotations or [])}")
        
        if not delete_clicks:
            print("DEBUG DELETE ID: No hay clicks, retornando")
            return annotations or [], no_update, False, "", None
            
        if delete_id is None:
            print("DEBUG DELETE ID: No se especificó ID")
            return annotations or [], no_update, True, "⚠️ Especifica un ID para eliminar", None
        
        if not annotations or len(annotations) == 0:
            print("DEBUG DELETE ID: No hay anotaciones")
            return annotations or [], no_update, True, "⚠️ No hay anotaciones en esta imagen", None
        
        try:
            print(f"DEBUG DELETE ID: Eliminando anotación con ID: {delete_id}")
            print(f"DEBUG DELETE ID: IDs disponibles: {[ann.get('id', 'sin-id') for ann in annotations]}")
            
            # Validar que el ID existe
            if delete_id < 0 or delete_id >= len(annotations):
                return annotations, no_update, True, f"⚠️ ID {delete_id} fuera de rango (0-{len(annotations)-1})", None
            
            # Guardar estado para undo ANTES de eliminar
            self.undo_manager.push_state(image_data['filename'], annotations)
            
            # Filtrar anotaciones (eliminar por ID)
            annotations_filtered = [ann for i, ann in enumerate(annotations) if i != delete_id]
            
            # Reindexar IDs
            for i, ann in enumerate(annotations_filtered):
                ann['id'] = i
            
            print(f"DEBUG DELETE ID: Anotación eliminada exitosamente. Quedan {len(annotations_filtered)} anotaciones")
            
            # Regenerar figura
            show_ids = 'show_ids' in (display_options or ['show_ids'])
            show_coords = 'show_coords' in (display_options or [])
            fig, _ = self.figure_generator.create_figure_with_annotations(
                image_data['filename'], annotations_filtered, opacity, show_ids, show_coords
            )
            
            # Guardar automáticamente
            try:
                self.annotation_manager.save_annotations(image_data['filename'], annotations_filtered)
                print("DEBUG DELETE ID: Guardado exitoso después de eliminar")
            except Exception as save_error:
                print(f"ERROR DELETE ID guardando automáticamente: {save_error}")
            
            # Limpiar el input field
            return annotations_filtered, fig, True, f"🗑️ Anotación ID {delete_id} eliminada - Guardado automático", None
            
        except Exception as e:
            print(f"ERROR DELETE ID eliminando anotación: {str(e)}")
            import traceback
            traceback.print_exc()
            return annotations or [], no_update, True, f"❌ Error eliminando anotación: {str(e)}", None
    
    def handle_undo_action(self, undo_clicks, image_data, opacity, display_options):
        """Deshacer última acción"""
        if not undo_clicks or not image_data:
            return no_update, no_update, False, ""
        
        try:
            # Recuperar estado anterior del stack de undo
            previous_state = self.undo_manager.pop_state()
            if not previous_state:
                return no_update, no_update, True, "⚠️ No hay acciones para deshacer"
            
            # Verificar que sea para la imagen correcta
            if previous_state['image_filename'] != image_data['filename']:
                # Si no es la misma imagen, devolver el estado al stack
                self.undo_manager.undo_stack.append(previous_state)
                return no_update, no_update, True, "⚠️ No hay acciones para deshacer en esta imagen"
            
            # Restaurar anotaciones
            annotations = previous_state['annotations']
            
            # Regenerar figura
            show_ids = 'show_ids' in (display_options or ['show_ids'])
            show_coords = 'show_coords' in (display_options or [])
            fig, _ = self.figure_generator.create_figure_with_annotations(
                image_data['filename'], annotations, opacity, show_ids, show_coords
            )
            
            # Guardar automáticamente
            try:
                self.annotation_manager.save_annotations(image_data['filename'], annotations)
            except Exception as save_error:
                print(f"Error guardando automáticamente: {save_error}")
            
            return annotations, fig, True, f"↶ Acción deshecha - {self.undo_manager.get_undo_count()} deshacer restantes"
            
        except Exception as e:
            return no_update, no_update, True, f"❌ Error deshaciendo: {str(e)}"
