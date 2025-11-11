"""
AI Models loader and inference functions.
Functional approach to managing AI models: DETR, OpenCLIP, PaddleOCR, InsightFace, PDQ Hash.

NOTE: PaddleOCR and InsightFace use ONNX Runtime which doesn't support CUDA 13 yet.
Both are configured to use CPU mode for compatibility. Performance is still good:
- PaddleOCR: ~100-200ms per image (CPU)
- InsightFace: ~50-100ms per image (CPU)
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

# Model imports
from transformers import AutoModel, AutoProcessor
import open_clip
from paddleocr import PaddleOCR
import insightface
import pdqhash
import cv2

from config import settings

# Setup logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


# Global model storage (functional singleton pattern)
_models_cache = {
    'initialized': False,
    'device': None,
    'detr_model': None,
    'detr_processor': None,
    'clip_model': None,
    'clip_preprocess': None,
    'clip_tokenizer': None,
    'ocr_model': None,
    'face_app': None
}


def _load_detr_model() -> None:
    """Load DETR model for object detection."""
    logger.info("Loading DETR model...")
    
    try:
        from transformers import DetrImageProcessor, DetrForObjectDetection
        device = _models_cache['device']
        
        # Load processor and model
        _models_cache['detr_processor'] = DetrImageProcessor.from_pretrained(
            settings.DETR_MODEL_NAME,
            cache_dir=settings.MODEL_CACHE_DIR
        )
        
        _models_cache['detr_model'] = DetrForObjectDetection.from_pretrained(
            settings.DETR_MODEL_NAME,
            cache_dir=settings.MODEL_CACHE_DIR
        ).eval()
        
        # Move to device and enable mixed precision
        if device == 'cuda':
            _models_cache['detr_model'] = _models_cache['detr_model'].cuda()
        
        logger.info(f"✓ DETR model loaded: {settings.DETR_MODEL_NAME}")
        
    except Exception as e:
        logger.error(f"✗ Failed to load DETR model: {e}")
        raise


def _load_openclip_model() -> None:
    """Load OpenCLIP model for semantic embeddings."""
    logger.info("Loading OpenCLIP model...")
    
    try:
        device = _models_cache['device']
        
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.OPENCLIP_MODEL_NAME,
            pretrained=settings.OPENCLIP_PRETRAINED,
            cache_dir=settings.MODEL_CACHE_DIR,
            device=device
        )
        
        model.eval()
        
        # Enable mixed precision
        if device == 'cuda':
            model = model.half()
        
        _models_cache['clip_model'] = model
        _models_cache['clip_preprocess'] = preprocess
        _models_cache['clip_tokenizer'] = open_clip.get_tokenizer(settings.OPENCLIP_MODEL_NAME)
        
        logger.info("✓ OpenCLIP model loaded")
        
    except Exception as e:
        logger.error(f"✗ Failed to load OpenCLIP model: {e}")
        raise


def _load_paddleocr_model() -> None:
    """Load PaddleOCR model for text extraction."""
    logger.info("Loading PaddleOCR model...")
    
    try:
        # Note: ONNX Runtime doesn't support CUDA 13 yet, so PaddleOCR will
        # automatically fall back to CPU if CUDA is unavailable for ONNX
        _models_cache['ocr_model'] = PaddleOCR(lang='en')
        
        logger.info(f"✓ PaddleOCR model loaded (ONNX will use CPU if CUDA 13 incompatible)")
        
    except Exception as e:
        logger.error(f"✗ Failed to load PaddleOCR model: {e}")
        raise


def _load_insightface_model() -> None:
    """Load InsightFace model for face detection."""
    logger.info("Loading InsightFace model...")
    
    try:
        device = _models_cache['device']
        
        # Force CPU mode - ONNX Runtime doesn't support CUDA 13 yet
        face_app = insightface.app.FaceAnalysis(
            name=settings.INSIGHTFACE_MODEL_NAME,
            root=str(settings.MODEL_CACHE_DIR / 'insightface'),
            providers=['CPUExecutionProvider']  # CPU mode for ONNX compatibility
        )
        
        # Prepare with CPU context
        ctx_id = -1  # CPU
        face_app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        
        _models_cache['face_app'] = face_app
        
        logger.info(f"✓ InsightFace model loaded (CPU mode for ONNX compatibility)")
        
    except Exception as e:
        logger.error(f"✗ Failed to load InsightFace model: {e}")
        raise


def initialize_models() -> None:
    """Initialize all models (only once)."""
    if _models_cache['initialized']:
        return
    
    logger.info("Initializing AI models...")
    logger.info(f"Device: {settings.DEVICE}")
    
    _models_cache['device'] = settings.DEVICE
    
    _load_detr_model()
    _load_openclip_model()
    _load_paddleocr_model()
    _load_insightface_model()
    
    _models_cache['initialized'] = True
    logger.info("✓ All AI models loaded successfully")


def recognize_objects_detr(image: Image.Image, confidence_threshold: float = 0.5) -> List[Dict[str, float]]:
    """
    Recognize objects in an image using DETR.
    
    Args:
        image: PIL Image
        confidence_threshold: Minimum confidence score (0-1)
        
    Returns:
        List of dicts with 'tag', 'confidence', and 'bbox' keys
    """
    if not _models_cache['initialized']:
        initialize_models()
    
    try:
        import torch
        
        processor = _models_cache['detr_processor']
        model = _models_cache['detr_model']
        device = _models_cache['device']
        
        # Prepare image
        inputs = processor(images=image, return_tensors="pt")
        
        # Move to device
        if device == 'cuda':
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Post-process results
        target_sizes = torch.tensor([image.size[::-1]])
        if device == 'cuda':
            target_sizes = target_sizes.cuda()
        
        results = processor.post_process_object_detection(
            outputs, 
            target_sizes=target_sizes, 
            threshold=confidence_threshold
        )[0]
        
        # Convert to our format
        detections = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            label_name = model.config.id2label[label.item()]
            confidence = score.item()
            bbox = box.tolist()
            
            detections.append({
                'tag': label_name,
                'confidence': confidence,
                'bbox': {
                    'x1': bbox[0],
                    'y1': bbox[1],
                    'x2': bbox[2],
                    'y2': bbox[3]
                }
            })
        
        logger.debug(f"DETR detected {len(detections)} objects")
        return detections
        
    except Exception as e:
        logger.error(f"Error in DETR object recognition: {e}")
        return []


def recognize_objects(image: Image.Image, confidence_threshold: float = 0.5) -> List[Dict[str, float]]:
    """
    Recognize objects in an image using DETR.
    
    Args:
        image: PIL Image
        confidence_threshold: Minimum confidence score (0-1)
        
    Returns:
        List of dicts with 'tag', 'confidence', and 'bbox' keys
    """
    return recognize_objects_detr(image, confidence_threshold)


def generate_image_embedding(image: Image.Image) -> np.ndarray:
    """
    Generate semantic embedding for an image using OpenCLIP.
    
    Args:
        image: PIL Image
        
    Returns:
        1024-dim numpy array
    """
    if not _models_cache['initialized']:
        initialize_models()
    
    try:
        device = _models_cache['device']
        clip_model = _models_cache['clip_model']
        clip_preprocess = _models_cache['clip_preprocess']
        
        # Preprocess image
        image_input = clip_preprocess(image).unsqueeze(0)
        
        if device == 'cuda':
            image_input = image_input.cuda().half()
        
        # Generate embedding
        with torch.no_grad():
            image_features = clip_model.encode_image(image_input)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy
        embedding = image_features.cpu().numpy().astype(np.float32)[0]
        
        logger.debug(f"Generated image embedding: shape {embedding.shape}")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating image embedding: {e}")
        return np.zeros(1024, dtype=np.float32)


def generate_text_embedding(text: str) -> np.ndarray:
    """
    Generate semantic embedding for text using OpenCLIP.
    
    Args:
        text: Text string
        
    Returns:
        1024-dim numpy array
    """
    if not _models_cache['initialized']:
        initialize_models()
    
    try:
        device = _models_cache['device']
        clip_model = _models_cache['clip_model']
        clip_tokenizer = _models_cache['clip_tokenizer']
        
        # Tokenize text
        text_input = clip_tokenizer([text])
        
        if device == 'cuda':
            text_input = text_input.cuda()
        
        # Generate embedding
        with torch.no_grad():
            text_features = clip_model.encode_text(text_input)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy
        embedding = text_features.cpu().numpy().astype(np.float32)[0]
        
        logger.debug(f"Generated text embedding: shape {embedding.shape}")
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating text embedding: {e}")
        return np.zeros(1024, dtype=np.float32)


def extract_text(image_path: str) -> Optional[str]:
    """
    Extract text from an image using PaddleOCR.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Extracted text or None if no text found
    """
    if not _models_cache['initialized']:
        initialize_models()
    
    try:
        ocr_model = _models_cache['ocr_model']
        result = ocr_model.ocr(image_path)
        
        if not result or not result[0]:
            logger.debug("No text detected in image")
            return None
        
        # Extract text from results
        texts = [
            line[1][0]
            for line in result[0]
            if line and len(line) >= 2
        ]
        
        extracted_text = ' '.join(texts)
        logger.debug(f"Extracted text: {len(extracted_text)} characters")
        
        return extracted_text if extracted_text else None
        
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return None


def detect_faces(image_path: str) -> List[Dict]:
    """
    Detect faces in an image using InsightFace.
    
    Args:
        image_path: Path to image file
        
    Returns:
        List of face dicts with 'bbox' and 'embedding' keys
    """
    if not _models_cache['initialized']:
        initialize_models()
    
    # Early return for invalid image
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to read image: {image_path}")
        return []
    
    try:
        face_app = _models_cache['face_app']
        faces = face_app.get(img)
        
        if not faces:
            logger.debug("No faces detected")
            return []
        
        # Extract face data
        face_data = [
            {
                'bbox': {
                    'x': bbox[0],
                    'y': bbox[1],
                    'width': bbox[2] - bbox[0],
                    'height': bbox[3] - bbox[1]
                },
                'embedding': face.normed_embedding.astype(np.float32)
            }
            for face in faces
            for bbox in [face.bbox.astype(int).tolist()]
        ]
        
        logger.debug(f"Detected {len(face_data)} faces")
        return face_data
        
    except Exception as e:
        logger.error(f"Error detecting faces: {e}")
        return []


def calculate_pdq_hash(image_path: str) -> Tuple[str, Optional[float]]:
    """
    Calculate PDQ hash for an image.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (hash_hex_string, quality_score)
    """
    # Early return for invalid image
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to read image: {image_path}")
        return ("", None)
    
    try:
        # Convert to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Calculate PDQ hash
        hash_vector, quality = pdqhash.compute(img_rgb)
        
        # Convert bit vector to hex string
        # pdqhash returns a numpy array of 256 bits (0s and 1s)
        # Convert to hex: group 8 bits into bytes, then convert to hex
        hash_bytes = bytearray()
        for i in range(0, len(hash_vector), 8):
            byte_bits = hash_vector[i:i+8]
            byte_val = int(''.join(str(int(b)) for b in byte_bits), 2)
            hash_bytes.append(byte_val)
        hash_hex = hash_bytes.hex()
        
        logger.debug(f"PDQ hash: {hash_hex[:16]}... (quality: {quality})")
        return (hash_hex, float(quality) if quality is not None else None)
        
    except Exception as e:
        logger.error(f"Error calculating PDQ hash: {e}")
        return ("", None)


def warmup_models() -> None:
    """Warmup models with dummy data to initialize CUDA."""
    logger.info("Warming up models...")
    
    # Ensure models are initialized
    initialize_models()
    
    # Create dummy image
    dummy_img = Image.new('RGB', (224, 224), color='white')
    
    try:
        # Warmup RAM++
        _ = recognize_objects(dummy_img)
        
        # Warmup OpenCLIP
        _ = generate_image_embedding(dummy_img)
        _ = generate_text_embedding("test")
        
        logger.info("✓ Models warmed up successfully")
        
    except Exception as e:
        logger.warning(f"Model warmup encountered errors: {e}")
