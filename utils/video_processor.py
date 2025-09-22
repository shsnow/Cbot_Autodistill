"""
Procesador de Videos - AutoDistill Suite
Extrae frames de videos para procesamiento con AutoDistill
"""

import cv2
import os
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import json
from .config import Config

class VideoProcessor:
    def __init__(self):
        self.supported_formats = Config.SUPPORTED_VIDEO_FORMATS
        
    def get_video_info(self, video_path):
        """Obtener información del video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                raise Exception("No se pudo abrir el video")
            
            # Obtener propiedades
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calcular duración
            duration_seconds = frame_count / fps if fps > 0 else 0
            duration = str(timedelta(seconds=int(duration_seconds)))
            
            # Tamaño del archivo
            file_size = os.path.getsize(video_path)
            size_mb = file_size / (1024 * 1024)
            
            cap.release()
            
            return {
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration,
                'duration_seconds': duration_seconds,
                'size_mb': size_mb,
                'codec': self._get_video_codec(video_path)
            }
            
        except Exception as e:
            raise Exception(f"Error obteniendo info del video: {str(e)}")
    
    def _get_video_codec(self, video_path):
        """Obtener codec del video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            fourcc = cap.get(cv2.CAP_PROP_FOURCC)
            cap.release()
            
            # Convertir fourcc a string
            codec = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])
            return codec.strip()
        except:
            return "Desconocido"
    
    def extract_frames(self, video_path, output_dir, frame_interval=30, 
                      max_frames=None, start_time=0, end_time=None, 
                      quality=95, callback=None):
        """
        Extraer frames del video
        
        Args:
            video_path: Ruta del video
            output_dir: Directorio de salida
            frame_interval: Extraer 1 frame cada N frames
            max_frames: Máximo número de frames (None = sin límite)
            start_time: Tiempo de inicio en segundos
            end_time: Tiempo de fin en segundos (None = hasta el final)
            quality: Calidad de compresión JPEG (1-100)
            callback: Función callback para progreso
        
        Returns:
            Dict con información del proceso
        """
        try:
            # Crear directorio de salida
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Abrir video
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise Exception("No se pudo abrir el video")
            
            # Obtener información del video
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calcular frames de inicio y fin
            start_frame = int(start_time * fps) if start_time else 0
            end_frame = int(end_time * fps) if end_time else total_frames
            
            # Ir al frame de inicio
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            extracted_frames = []
            current_frame = start_frame
            extracted_count = 0
            
            while current_frame < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extraer frame según el intervalo
                if (current_frame - start_frame) % frame_interval == 0:
                    # Nombre del archivo
                    frame_filename = f"frame_{current_frame:06d}.jpg"
                    frame_path = output_path / frame_filename
                    
                    # Guardar frame
                    success = cv2.imwrite(str(frame_path), frame, 
                                        [cv2.IMWRITE_JPEG_QUALITY, quality])
                    
                    if success:
                        extracted_frames.append({
                            'filename': frame_filename,
                            'path': str(frame_path),
                            'frame_number': current_frame,
                            'timestamp': current_frame / fps
                        })
                        extracted_count += 1
                        
                        # Callback de progreso
                        if callback:
                            progress = (current_frame - start_frame) / (end_frame - start_frame) * 100
                            callback({
                                'progress': progress,
                                'current_frame': current_frame,
                                'extracted_count': extracted_count,
                                'current_file': frame_filename
                            })
                        
                        # Verificar límite máximo
                        if max_frames and extracted_count >= max_frames:
                            break
                
                current_frame += 1
            
            cap.release()
            
            # Información del proceso
            result = {
                'success': True,
                'video_path': str(video_path),
                'output_dir': str(output_dir),
                'extracted_count': extracted_count,
                'total_frames_processed': current_frame - start_frame,
                'frame_interval': frame_interval,
                'quality': quality,
                'extracted_frames': extracted_frames,
                'processing_time': datetime.now().isoformat(),
                'start_frame': start_frame,
                'end_frame': current_frame
            }
            
            # Guardar metadata
            metadata_path = output_path / "extraction_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'video_path': str(video_path),
                'output_dir': str(output_dir)
            }
    
    def create_preview_gif(self, video_path, output_path, duration=5, fps=10, max_width=400):
        """Crear GIF de preview del video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise Exception("No se pudo abrir el video")
            
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calcular frames para el GIF
            frames_to_extract = duration * fps
            frame_interval = max(1, total_frames // frames_to_extract)
            
            frames = []
            current_frame = 0
            
            while len(frames) < frames_to_extract and current_frame < total_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = cap.read()
                
                if ret:
                    # Redimensionar si es necesario
                    height, width = frame.shape[:2]
                    if width > max_width:
                        scale = max_width / width
                        new_width = max_width
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    # Convertir BGR a RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frames.append(frame_rgb)
                
                current_frame += frame_interval
            
            cap.release()
            
            # Crear GIF usando imageio si está disponible
            try:
                import imageio
                imageio.mimsave(str(output_path), frames, duration=1/fps)
                return True
            except ImportError:
                # Fallback: guardar solo el primer frame como imagen
                if frames:
                    from PIL import Image
                    img = Image.fromarray(frames[0])
                    preview_path = str(output_path).replace('.gif', '_preview.jpg')
                    img.save(preview_path)
                    return preview_path
                return False
                
        except Exception as e:
            print(f"Error creando preview: {e}")
            return False
    
    def batch_process_videos(self, video_list, base_output_dir, frame_interval=30, 
                           quality=95, callback=None):
        """Procesar múltiples videos en lote"""
        results = []
        
        for i, video_path in enumerate(video_list):
            try:
                # Crear carpeta individual para cada video
                video_name = Path(video_path).stem
                output_dir = Path(base_output_dir) / video_name
                
                # Callback de progreso general
                if callback:
                    callback({
                        'type': 'video_start',
                        'video_index': i + 1,
                        'total_videos': len(video_list),
                        'video_name': video_name,
                        'video_path': video_path
                    })
                
                # Extraer frames
                def frame_callback(progress_info):
                    if callback:
                        progress_info['type'] = 'frame_progress'
                        progress_info['video_index'] = i + 1
                        progress_info['total_videos'] = len(video_list)
                        callback(progress_info)
                
                result = self.extract_frames(
                    video_path=video_path,
                    output_dir=output_dir,
                    frame_interval=frame_interval,
                    quality=quality,
                    callback=frame_callback
                )
                
                results.append(result)
                
                # Callback de video completado
                if callback:
                    callback({
                        'type': 'video_complete',
                        'video_index': i + 1,
                        'total_videos': len(video_list),
                        'result': result
                    })
                    
            except Exception as e:
                error_result = {
                    'success': False,
                    'error': str(e),
                    'video_path': video_path
                }
                results.append(error_result)
        
        return results