"""
Gestor de Datasets - AutoDistill Suite
Organiza y gestiona datasets para entrenamiento
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import random
from .config import Config

class DatasetManager:
    def __init__(self):
        self.config = Config()
        
    def create_yolo_dataset(self, source_dir, output_dir, train_split=0.7, 
                          val_split=0.2, test_split=0.1, classes=None):
        """
        Crear dataset en formato YOLO
        
        Args:
            source_dir: Directorio con imágenes y anotaciones
            output_dir: Directorio de salida
            train_split, val_split, test_split: Porcentajes de división
            classes: Lista de clases (se detecta automáticamente si es None)
        """
        try:
            source_path = Path(source_dir)
            output_path = Path(output_dir)
            
            # Verificar que los porcentajes sumen 1
            total_split = train_split + val_split + test_split
            if abs(total_split - 1.0) > 0.01:
                raise ValueError("Los porcentajes de división deben sumar 1.0")
            
            # Obtener archivos de imágenes
            image_files = []
            for ext in Config.SUPPORTED_IMAGE_FORMATS:
                image_files.extend(source_path.glob(f"*{ext}"))
            
            if not image_files:
                raise Exception("No se encontraron imágenes en el directorio fuente")
            
            # Detectar clases automáticamente si no se proporcionan
            if classes is None:
                classes = self._detect_classes_from_labels(source_path)
            
            # Crear estructura de directorios
            self._create_yolo_structure(output_path)
            
            # Mezclar y dividir archivos
            random.shuffle(image_files)
            
            train_count = int(len(image_files) * train_split)
            val_count = int(len(image_files) * val_split)
            
            train_files = image_files[:train_count]
            val_files = image_files[train_count:train_count + val_count]
            test_files = image_files[train_count + val_count:]
            
            # Copiar archivos a sus respectivos directorios
            splits = {
                'train': train_files,
                'val': val_files,
                'test': test_files
            }
            
            dataset_info = {
                'created': datetime.now().isoformat(),
                'source_dir': str(source_dir),
                'output_dir': str(output_dir),
                'classes': classes,
                'splits': {},
                'total_images': len(image_files)
            }
            
            for split_name, files in splits.items():
                if not files:  # Skip empty splits
                    continue
                    
                images_dir = output_path / split_name / "images"
                labels_dir = output_path / split_name / "labels"
                
                copied_images = 0
                copied_labels = 0
                
                for img_file in files:
                    # Copiar imagen
                    dst_img = images_dir / img_file.name
                    shutil.copy2(img_file, dst_img)
                    copied_images += 1
                    
                    # Copiar etiqueta si existe
                    label_file = source_path / f"{img_file.stem}.txt"
                    if label_file.exists():
                        dst_label = labels_dir / f"{img_file.stem}.txt"
                        shutil.copy2(label_file, dst_label)
                        copied_labels += 1
                
                dataset_info['splits'][split_name] = {
                    'images': copied_images,
                    'labels': copied_labels,
                    'percentage': len(files) / len(image_files) * 100
                }
            
            # Crear archivo de configuración YAML
            self._create_yaml_config(output_path, classes, dataset_info)
            
            # Guardar metadata
            metadata_file = output_path / "dataset_info.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(dataset_info, f, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'dataset_info': dataset_info,
                'output_dir': str(output_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source_dir': str(source_dir),
                'output_dir': str(output_dir)
            }
    
    def _detect_classes_from_labels(self, source_dir):
        """Detectar clases automáticamente de los archivos de etiquetas"""
        classes_set = set()
        
        for label_file in Path(source_dir).glob("*.txt"):
            try:
                with open(label_file, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            class_id = int(parts[0])
                            classes_set.add(class_id)
            except (ValueError, IndexError):
                continue
        
        # Crear lista de clases ordenada
        if classes_set:
            max_class = max(classes_set)
            classes = [f"class_{i}" for i in range(max_class + 1)]
            return classes
        else:
            return ["class_0"]  # Clase por defecto
    
    def _create_yolo_structure(self, output_path):
        """Crear estructura de directorios YOLO"""
        splits = ['train', 'val', 'test']
        subdirs = ['images', 'labels']
        
        for split in splits:
            for subdir in subdirs:
                dir_path = output_path / split / subdir
                dir_path.mkdir(parents=True, exist_ok=True)
    
    def _create_yaml_config(self, output_path, classes, dataset_info):
        """Crear archivo de configuración YAML para YOLO"""
        yaml_content = f"""# Dataset configuration for YOLO
# Generated by AutoDistill Suite on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Dataset paths
path: {output_path.absolute()}
train: train/images
val: val/images
test: test/images

# Number of classes
nc: {len(classes)}

# Class names
names:
"""
        
        for i, class_name in enumerate(classes):
            yaml_content += f"  {i}: {class_name}\n"
        
        yaml_content += f"""
# Dataset statistics
total_images: {dataset_info['total_images']}
splits:
"""
        
        for split_name, split_info in dataset_info['splits'].items():
            yaml_content += f"  {split_name}: {split_info['images']} images\n"
        
        # Guardar archivo YAML
        yaml_file = output_path / "dataset.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
    
    def validate_dataset(self, dataset_dir):
        """Validar la estructura y contenido del dataset"""
        try:
            dataset_path = Path(dataset_dir)
            
            if not dataset_path.exists():
                return {'valid': False, 'error': 'Dataset directory does not exist'}
            
            issues = []
            warnings = []
            stats = {}
            
            # Verificar estructura de directorios
            required_dirs = ['train/images', 'train/labels']
            optional_dirs = ['val/images', 'val/labels', 'test/images', 'test/labels']
            
            for dir_path in required_dirs:
                if not (dataset_path / dir_path).exists():
                    issues.append(f"Missing required directory: {dir_path}")
            
            # Verificar archivos YAML
            yaml_file = dataset_path / "dataset.yaml"
            if not yaml_file.exists():
                warnings.append("Missing dataset.yaml configuration file")
            
            # Validar cada split
            for split in ['train', 'val', 'test']:
                images_dir = dataset_path / split / "images"
                labels_dir = dataset_path / split / "labels"
                
                if images_dir.exists():
                    # Contar imágenes
                    image_files = []
                    for ext in Config.SUPPORTED_IMAGE_FORMATS:
                        image_files.extend(images_dir.glob(f"*{ext}"))
                    
                    # Contar etiquetas
                    label_files = list(labels_dir.glob("*.txt")) if labels_dir.exists() else []
                    
                    # Verificar correspondencia
                    orphaned_images = []
                    orphaned_labels = []
                    
                    for img_file in image_files:
                        label_file = labels_dir / f"{img_file.stem}.txt"
                        if not label_file.exists():
                            orphaned_images.append(img_file.name)
                    
                    if labels_dir.exists():
                        for label_file in label_files:
                            img_files = [images_dir / f"{label_file.stem}{ext}" 
                                       for ext in Config.SUPPORTED_IMAGE_FORMATS]
                            if not any(img.exists() for img in img_files):
                                orphaned_labels.append(label_file.name)
                    
                    stats[split] = {
                        'images': len(image_files),
                        'labels': len(label_files),
                        'orphaned_images': len(orphaned_images),
                        'orphaned_labels': len(orphaned_labels)
                    }
                    
                    if orphaned_images:
                        warnings.append(f"{split}: {len(orphaned_images)} images without labels")
                    if orphaned_labels:
                        warnings.append(f"{split}: {len(orphaned_labels)} labels without images")
            
            # Validar formato de etiquetas
            label_issues = self._validate_label_format(dataset_path)
            issues.extend(label_issues)
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Validation error: {str(e)}"
            }
    
    def _validate_label_format(self, dataset_path):
        """Validar formato de archivos de etiquetas YOLO"""
        issues = []
        
        for split in ['train', 'val', 'test']:
            labels_dir = dataset_path / split / "labels"
            if not labels_dir.exists():
                continue
            
            for label_file in labels_dir.glob("*.txt"):
                try:
                    with open(label_file, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:  # Skip empty lines
                                continue
                            
                            parts = line.split()
                            if len(parts) != 5:
                                issues.append(f"{label_file.name}:{line_num} - Invalid format (expected 5 values)")
                                continue
                            
                            try:
                                class_id = int(parts[0])
                                x_center = float(parts[1])
                                y_center = float(parts[2])
                                width = float(parts[3])
                                height = float(parts[4])
                                
                                # Validar rangos
                                if not (0 <= x_center <= 1):
                                    issues.append(f"{label_file.name}:{line_num} - x_center out of range [0,1]")
                                if not (0 <= y_center <= 1):
                                    issues.append(f"{label_file.name}:{line_num} - y_center out of range [0,1]")
                                if not (0 < width <= 1):
                                    issues.append(f"{label_file.name}:{line_num} - width out of range (0,1]")
                                if not (0 < height <= 1):
                                    issues.append(f"{label_file.name}:{line_num} - height out of range (0,1]")
                                
                            except ValueError:
                                issues.append(f"{label_file.name}:{line_num} - Invalid numeric values")
                                
                except Exception as e:
                    issues.append(f"Error reading {label_file.name}: {str(e)}")
        
        return issues
    
    def get_dataset_statistics(self, dataset_dir):
        """Obtener estadísticas detalladas del dataset"""
        try:
            validation = self.validate_dataset(dataset_dir)
            if not validation['valid']:
                return validation
            
            dataset_path = Path(dataset_dir)
            stats = {
                'overview': validation['stats'],
                'class_distribution': {},
                'image_sizes': {},
                'annotation_density': {}
            }
            
            # Analizar distribución de clases
            all_classes = {}
            
            for split in ['train', 'val', 'test']:
                labels_dir = dataset_path / split / "labels"
                if not labels_dir.exists():
                    continue
                
                split_classes = {}
                split_annotations = 0
                
                for label_file in labels_dir.glob("*.txt"):
                    try:
                        with open(label_file, 'r') as f:
                            for line in f:
                                parts = line.strip().split()
                                if len(parts) == 5:
                                    class_id = int(parts[0])
                                    split_classes[class_id] = split_classes.get(class_id, 0) + 1
                                    all_classes[class_id] = all_classes.get(class_id, 0) + 1
                                    split_annotations += 1
                    except:
                        continue
                
                stats['class_distribution'][split] = split_classes
                stats['annotation_density'][split] = split_annotations
            
            stats['class_distribution']['total'] = all_classes
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }