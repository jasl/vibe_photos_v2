"""
Image utility functions for format conversion and thumbnail generation.
Handles HEIC, RAW formats, and creates standardized JPEG thumbnails.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import pillow_heif
import rawpy
import numpy as np
from config import settings

# Register HEIF opener with PIL
pillow_heif.register_heif_opener()


class ImageConversionError(Exception):
    """Exception raised when image conversion fails."""
    pass


def is_raw_format(file_path: Path) -> bool:
    """Check if file is a RAW image format."""
    raw_extensions = {'.cr2', '.nef', '.dng', '.arw', '.raw', '.orf', '.rw2', '.pef'}
    return file_path.suffix.lower() in raw_extensions


def is_heic_format(file_path: Path) -> bool:
    """Check if file is a HEIC/HEIF format."""
    heic_extensions = {'.heic', '.heif'}
    return file_path.suffix.lower() in heic_extensions


def convert_raw_to_jpeg(raw_path: Path, output_path: Path) -> Tuple[int, int]:
    """
    Convert RAW image to JPEG format.
    
    Args:
        raw_path: Path to RAW image file
        output_path: Path for output JPEG file
        
    Returns:
        Tuple of (width, height) of the converted image
        
    Raises:
        ImageConversionError: If conversion fails
    """
    try:
        with rawpy.imread(str(raw_path)) as raw:
            # Process RAW image with default parameters
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=False,
                no_auto_bright=False,
                output_bps=8
            )
            
            # Convert numpy array to PIL Image
            image = Image.fromarray(rgb)
            
            # Save as JPEG with good quality
            image.save(output_path, 'JPEG', quality=95, optimize=True)
            
            return image.size
            
    except Exception as e:
        raise ImageConversionError(f"Failed to convert RAW image {raw_path}: {e}")


def convert_heic_to_jpeg(heic_path: Path, output_path: Path) -> Tuple[int, int]:
    """
    Convert HEIC/HEIF image to JPEG format.
    
    Args:
        heic_path: Path to HEIC image file
        output_path: Path for output JPEG file
        
    Returns:
        Tuple of (width, height) of the converted image
        
    Raises:
        ImageConversionError: If conversion fails
    """
    try:
        # PIL with pillow_heif can open HEIC directly
        image = Image.open(heic_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Save as JPEG
        image.save(output_path, 'JPEG', quality=95, optimize=True)
        
        return image.size
        
    except Exception as e:
        raise ImageConversionError(f"Failed to convert HEIC image {heic_path}: {e}")


def convert_to_jpeg(input_path: Path, output_dir: Optional[Path] = None) -> Tuple[Path, Tuple[int, int]]:
    """
    Convert image to JPEG format if needed.
    
    Args:
        input_path: Path to input image
        output_dir: Directory for converted image (default: same as input)
        
    Returns:
        Tuple of (output_path, (width, height))
        If already JPEG, returns original path
        
    Raises:
        ImageConversionError: If conversion fails
    """
    input_path = Path(input_path)
    
    # Check if already JPEG
    if input_path.suffix.lower() in {'.jpg', '.jpeg'}:
        try:
            with Image.open(input_path) as img:
                return input_path, img.size
        except Exception as e:
            raise ImageConversionError(f"Failed to open JPEG image {input_path}: {e}")
    
    # Determine output path
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{input_path.stem}.jpg"
    
    # Convert based on format
    if is_raw_format(input_path):
        size = convert_raw_to_jpeg(input_path, output_path)
    elif is_heic_format(input_path):
        size = convert_heic_to_jpeg(input_path, output_path)
    else:
        # Try to open with PIL for other formats (PNG, WebP, etc.)
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                size = img.size
                img.save(output_path, 'JPEG', quality=95, optimize=True)
        except Exception as e:
            raise ImageConversionError(f"Failed to convert image {input_path}: {e}")
    
    return output_path, size


def generate_thumbnail(
    image_path: Path,
    thumbnail_dir: Optional[Path] = None,
    max_size: int = 400
) -> Path:
    """
    Generate thumbnail for an image.
    
    Args:
        image_path: Path to original image
        thumbnail_dir: Directory to save thumbnail (default: from settings)
        max_size: Maximum dimension for thumbnail (default: 400)
        
    Returns:
        Path to generated thumbnail
        
    Raises:
        ImageConversionError: If thumbnail generation fails
    """
    if thumbnail_dir is None:
        thumbnail_dir = settings.THUMBNAIL_DIR
    else:
        thumbnail_dir = Path(thumbnail_dir)
    
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    # Create thumbnail filename
    thumbnail_filename = f"thumb_{image_path.stem}.jpg"
    thumbnail_path = thumbnail_dir / thumbnail_filename
    
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Calculate thumbnail size maintaining aspect ratio
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save thumbnail
            img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
            
            return thumbnail_path
            
    except Exception as e:
        raise ImageConversionError(f"Failed to generate thumbnail for {image_path}: {e}")


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """
    Get image dimensions without loading the entire image into memory.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (width, height)
        
    Raises:
        ImageConversionError: If unable to read dimensions
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        raise ImageConversionError(f"Failed to get dimensions for {image_path}: {e}")


def get_file_size(file_path: Path) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def process_image_for_storage(
    image_path: Path,
    convert_to_jpg: bool = True
) -> dict:
    """
    Process image for storage: convert if needed and generate thumbnail.
    
    Args:
        image_path: Path to original image
        convert_to_jpg: Whether to convert non-JPEG formats
        
    Returns:
        Dict with processing results:
        {
            'processed_path': Path to processed image (JPEG),
            'thumbnail_path': Path to thumbnail,
            'width': Image width,
            'height': Image height,
            'file_size': File size in bytes,
            'original_format': Original file format
        }
        
    Raises:
        ImageConversionError: If processing fails
    """
    image_path = Path(image_path)
    original_format = image_path.suffix.lower()
    
    result = {
        'original_format': original_format,
        'original_path': image_path
    }
    
    # Convert to JPEG if needed
    if convert_to_jpg:
        processed_path, size = convert_to_jpeg(image_path)
        result['processed_path'] = processed_path
        result['width'], result['height'] = size
        result['file_size'] = get_file_size(processed_path)
    else:
        result['processed_path'] = image_path
        result['width'], result['height'] = get_image_dimensions(image_path)
        result['file_size'] = get_file_size(image_path)
    
    # Generate thumbnail
    result['thumbnail_path'] = generate_thumbnail(
        result['processed_path'],
        max_size=settings.THUMBNAIL_SIZE
    )
    
    return result


def is_supported_format(file_path: Path) -> bool:
    """
    Check if file format is supported for processing.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if format is supported
    """
    extension = file_path.suffix.lower().lstrip('.')
    return extension in settings.SUPPORTED_FORMATS

