"""
Celery tasks for image processing with state machine implementation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from celery import Task
from sqlalchemy import text
from workers.celery_app import app
from workers import ai_models
from models import (
    Photo, DetectedObject, PhotoTag, SemanticEmbedding, OCRText,
    Face, PhotoHash, Duplicate, TagCategoryMapping,
    PhotoState, get_session
)
from utils import process_image_for_storage, ImageConversionError
from config import settings
from workers.object_filtering import filter_detected_objects

logger = logging.getLogger(__name__)


class PhotoProcessingTask(Task):
    """Base task class with retry and error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True


def update_photo_state(session, photo_id: int, state: PhotoState, error_message: Optional[str] = None):
    """Update photo processing state."""
    photo = session.query(Photo).filter_by(id=photo_id).first()
    if photo:
        photo.state = state
        if error_message:
            photo.error_message = error_message
        if state in (PhotoState.COMPLETED, PhotoState.PARTIAL, PhotoState.FAILED):
            photo.processed_at = datetime.utcnow()
        session.commit()
        logger.info(f"Photo {photo_id} state: {state.value}")


@app.task(base=PhotoProcessingTask, bind=True, name='process_single_image')
def process_single_image(self, photo_id: int):
    """
    Process a single image through the complete AI pipeline.
    Implements state machine for tracking progress.
    
    States: pending → preprocessing → processing_objects → processing_embeddings 
    → processing_ocr → processing_faces → processing_hash → checking_duplicates 
    → completed/partial/failed
    """
    session = get_session()
    
    try:
        # Get photo record
        photo = session.query(Photo).filter_by(id=photo_id).first()
        if not photo:
            logger.error(f"Photo {photo_id} not found")
            return {'status': 'failed', 'error': 'Photo not found'}
        
        logger.info(f"Processing photo {photo_id}: {photo.filename}")
        
        # Ensure AI models are initialized
        ai_models.initialize_models()
        
        results = {
            'photo_id': photo_id,
            'filename': photo.filename,
            'steps_completed': [],
            'steps_failed': []
        }
        
        # Step 1: Preprocessing (convert format, generate thumbnail)
        try:
            update_photo_state(session, photo_id, PhotoState.PREPROCESSING)
            
            image_data = process_image_for_storage(Path(photo.file_path))
            
            # Update photo with processed information
            photo.thumbnail_path = str(image_data['thumbnail_path'])
            photo.width = image_data['width']
            photo.height = image_data['height']
            photo.file_size = image_data['file_size']
            session.commit()
            
            results['steps_completed'].append('preprocessing')
            logger.info(f"✓ Preprocessing complete: {photo.filename}")
            
        except Exception as e:
            logger.error(f"✗ Preprocessing failed: {e}")
            results['steps_failed'].append('preprocessing')
            # Continue with original file
        
        # Get the processed image path (or original if conversion failed)
        image_path = str(image_data.get('processed_path', photo.file_path))
        
        # Step 2: Object Recognition (DETR)
        try:
            update_photo_state(session, photo_id, PhotoState.PROCESSING_OBJECTS)
            
            from PIL import Image
            image = Image.open(image_path)
            
            detected_objects = ai_models.recognize_objects(image)
            image_width, image_height = image.size

            filtered_objects, filtered_out = filter_detected_objects(
                detected_objects, image_width, image_height
            )
            if filtered_out:
                logger.info(
                    "Filtered out %s detections due to area/conf thresholds",
                    filtered_out
                )

            # Deduplicate tags for PhotoTag (keep highest confidence per tag)
            unique_tags = {}
            for obj in filtered_objects:
                tag = obj['tag']
                if tag not in unique_tags or obj['confidence'] > unique_tags[tag]['confidence']:
                    unique_tags[tag] = obj

            # Find category for tags (do this once for all tags)
            tag_category_map = {}
            for tag in unique_tags.keys():
                tag_mapping = session.query(TagCategoryMapping).filter_by(tag=tag).first()
                tag_category_map[tag] = tag_mapping.category_id if tag_mapping else None

            # Save unique tags to PhotoTag
            for tag, obj in unique_tags.items():
                photo_tag = PhotoTag(
                    photo_id=photo_id,
                    tag=tag,
                    confidence=obj['confidence'],
                    category_id=tag_category_map[tag]
                )
                session.add(photo_tag)

            # Save all instances to DetectedObject (with bbox)
            for obj in filtered_objects:
                tag = obj['tag']
                detected_obj = DetectedObject(
                    photo_id=photo_id,
                    tag=tag,
                    confidence=obj['confidence'],
                    category_id=tag_category_map.get(tag),
                    bbox=obj.get('bbox')  # DETR already returns this
                )
                session.add(detected_obj)

            session.commit()
            results['detected_objects_count'] = len(filtered_objects)
            results['filtered_out_objects_count'] = filtered_out
            results['unique_tags_count'] = len(unique_tags)
            results['steps_completed'].append('objects')
            logger.info(
                "✓ Detected %s objects after filtering (%s unique tags)",
                len(filtered_objects),
                len(unique_tags)
            )
            
        except Exception as e:
            logger.error(f"✗ Object recognition failed: {e}")
            results['steps_failed'].append('objects')
        
        # Step 3: Semantic Embeddings (OpenCLIP)
        try:
            update_photo_state(session, photo_id, PhotoState.PROCESSING_EMBEDDINGS)
            
            from PIL import Image
            image = Image.open(image_path)
            
            embedding = ai_models.generate_image_embedding(image)
            
            # Store embedding
            semantic_emb = SemanticEmbedding(
                photo_id=photo_id,
                embedding=embedding.tolist(),
                model_version="ViT-H-14/laion2b_s32b_b79k"
            )
            session.add(semantic_emb)
            session.commit()
            
            results['steps_completed'].append('embeddings')
            logger.info(f"✓ Generated semantic embedding")
            
        except Exception as e:
            logger.error(f"✗ Semantic embedding failed: {e}")
            results['steps_failed'].append('embeddings')
        
        # Step 4: OCR (PaddleOCR)
        try:
            update_photo_state(session, photo_id, PhotoState.PROCESSING_OCR)
            
            extracted_text = ai_models.extract_text(image_path)
            
            if extracted_text and len(extracted_text.strip()) > 0:
                # Create ts_vector for full-text search
                ocr_text = OCRText(
                    photo_id=photo_id,
                    extracted_text=extracted_text,
                    language='en'
                )
                session.add(ocr_text)
                session.flush()
                
                # Update ts_vector using PostgreSQL function
                session.execute(
                    text(
                        "UPDATE ocr_texts SET ts_vector = to_tsvector('english', :text) "
                        "WHERE photo_id = :photo_id"
                    ),
                    {'text': extracted_text, 'photo_id': photo_id}
                )
                session.commit()
                
                results['ocr_text_length'] = len(extracted_text)
                results['steps_completed'].append('ocr')
                logger.info(f"✓ Extracted text: {len(extracted_text)} characters")
            else:
                logger.info("No text detected in image")
                results['steps_completed'].append('ocr')
            
        except Exception as e:
            logger.error(f"✗ OCR failed: {e}")
            results['steps_failed'].append('ocr')
        
        # Step 5: Face Detection (InsightFace)
        try:
            update_photo_state(session, photo_id, PhotoState.PROCESSING_FACES)
            
            faces = ai_models.detect_faces(image_path)
            
            for face_data in faces:
                face = Face(
                    photo_id=photo_id,
                    bbox=face_data['bbox'],
                    embedding=face_data['embedding'].tolist(),
                    cluster_id=None  # Clustering will be done later
                )
                session.add(face)
            
            session.commit()
            results['faces_count'] = len(faces)
            results['steps_completed'].append('faces')
            logger.info(f"✓ Detected {len(faces)} faces")
            
        except Exception as e:
            logger.error(f"✗ Face detection failed: {e}")
            results['steps_failed'].append('faces')
        
        # Step 6: PDQ Hash (pdqhash)
        try:
            update_photo_state(session, photo_id, PhotoState.PROCESSING_HASH)
            
            hash_hex, quality = ai_models.calculate_pdq_hash(image_path)
            
            if hash_hex:
                photo_hash = PhotoHash(
                    photo_id=photo_id,
                    pdq_hash=hash_hex,
                    quality_score=quality
                )
                session.add(photo_hash)
                session.commit()
                
                results['pdq_hash'] = hash_hex[:16] + "..."
                results['steps_completed'].append('hash')
                logger.info(f"✓ Calculated PDQ hash")
            
        except Exception as e:
            logger.error(f"✗ PDQ hash calculation failed: {e}")
            results['steps_failed'].append('hash')
        
        # Step 7: Check for Duplicates
        try:
            update_photo_state(session, photo_id, PhotoState.CHECKING_DUPLICATES)
            
            current_hash = session.query(PhotoHash).filter_by(photo_id=photo_id).first()
            
            if current_hash:
                # Find similar hashes using Hamming distance
                # Note: This is a simple implementation; for production, use specialized index
                other_hashes = session.query(PhotoHash).filter(
                    PhotoHash.photo_id != photo_id
                ).all()
                
                duplicates_found = 0
                for other_hash in other_hashes:
                    # Calculate Hamming distance
                    distance = sum(c1 != c2 for c1, c2 in zip(current_hash.pdq_hash, other_hash.pdq_hash))
                    
                    if distance <= settings.DUPLICATE_THRESHOLD:
                        # Check if duplicate relationship already exists
                        existing = session.query(Duplicate).filter(
                            ((Duplicate.photo_id_1 == photo_id) & (Duplicate.photo_id_2 == other_hash.photo_id)) |
                            ((Duplicate.photo_id_1 == other_hash.photo_id) & (Duplicate.photo_id_2 == photo_id))
                        ).first()
                        
                        if not existing:
                            duplicate = Duplicate(
                                photo_id_1=photo_id,
                                photo_id_2=other_hash.photo_id,
                                hamming_distance=distance
                            )
                            session.add(duplicate)
                            duplicates_found += 1
                
                session.commit()
                results['duplicates_found'] = duplicates_found
                results['steps_completed'].append('duplicates')
                logger.info(f"✓ Found {duplicates_found} duplicates")
            
        except Exception as e:
            logger.error(f"✗ Duplicate checking failed: {e}")
            results['steps_failed'].append('duplicates')
        
        # Determine final state
        if len(results['steps_failed']) == 0:
            final_state = PhotoState.COMPLETED
            results['status'] = 'completed'
        elif len(results['steps_completed']) > 0:
            final_state = PhotoState.PARTIAL
            results['status'] = 'partial'
        else:
            final_state = PhotoState.FAILED
            results['status'] = 'failed'
        
        update_photo_state(session, photo_id, final_state)
        
        logger.info(f"Processing complete for photo {photo_id}: {results['status']}")
        logger.info(f"  Completed steps: {results['steps_completed']}")
        if results['steps_failed']:
            logger.warning(f"  Failed steps: {results['steps_failed']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Fatal error processing photo {photo_id}: {e}")
        update_photo_state(session, photo_id, PhotoState.FAILED, str(e))
        return {'status': 'failed', 'error': str(e)}
        
    finally:
        session.close()

