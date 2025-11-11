"""
Hybrid search service implementing keyword search, semantic vector search, and RRF fusion.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from sqlalchemy import func, or_, and_, text
from sqlalchemy.orm import Session

from models import (
    Photo, DetectedObject, OCRText, SemanticEmbedding,
    Category, PhotoState, get_session
)
from workers import ai_models
from config import settings

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    keyword_results: List[Tuple[int, float]],
    semantic_results: List[Tuple[int, float]],
    k: int = 60
) -> List[Tuple[int, float]]:
    """
    Combine results from keyword and semantic search using Reciprocal Rank Fusion (RRF).
    
    Args:
        keyword_results: List of (photo_id, score) from keyword search
        semantic_results: List of (photo_id, distance) from vector search
        k: RRF constant (default: 60)
        
    Returns:
        List of (photo_id, rrf_score) sorted by score descending
    """
    # Create rank dictionaries
    keyword_ranks = {photo_id: rank for rank, (photo_id, _) in enumerate(keyword_results, 1)}
    semantic_ranks = {photo_id: rank for rank, (photo_id, _) in enumerate(semantic_results, 1)}
    
    # Combine all unique photo IDs
    all_photo_ids = set(keyword_ranks.keys()) | set(semantic_ranks.keys())
    
    # Calculate RRF scores
    rrf_scores = {}
    for photo_id in all_photo_ids:
        score = 0.0
        
        if photo_id in keyword_ranks:
            score += 1.0 / (k + keyword_ranks[photo_id])
        
        if photo_id in semantic_ranks:
            score += 1.0 / (k + semantic_ranks[photo_id])
        
        rrf_scores[photo_id] = score
    
    # Sort by score descending
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_results


def keyword_search(
    session: Session,
    query: str,
    limit: int = 100,
    categories: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Tuple[int, float]]:
    """
    Perform keyword search using PostgreSQL full-text search.
    
    Args:
        session: Database session
        query: Search query string
        limit: Maximum number of results
        categories: Optional list of category names to filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        
    Returns:
        List of (photo_id, relevance_score) sorted by relevance
    """
    try:
        # Create ts_query from search query
        ts_query = func.plainto_tsquery('english', query)
        
        # Build base query for OCR text search
        ocr_query = session.query(
            OCRText.photo_id,
            func.ts_rank(OCRText.ts_vector, ts_query).label('rank')
        ).filter(
            OCRText.ts_vector.op('@@')(ts_query)
        )
        
        # Build base query for tag search
        tag_query = session.query(
            DetectedObject.photo_id,
            func.avg(DetectedObject.confidence).label('rank')
        ).filter(
            DetectedObject.tag.ilike(f'%{query}%')
        ).group_by(DetectedObject.photo_id)
        
        # Apply category filter to tag query
        if categories:
            category_ids = session.query(Category.id).filter(
                Category.name.in_(categories)
            ).all()
            category_ids = [cid[0] for cid in category_ids]
            
            if category_ids:
                tag_query = tag_query.filter(DetectedObject.category_id.in_(category_ids))
        
        # Combine OCR and tag results
        ocr_results = {photo_id: rank for photo_id, rank in ocr_query.all()}
        tag_results = {photo_id: rank for photo_id, rank in tag_query.all()}
        
        # Merge results (sum scores for photos appearing in both)
        all_photo_ids = set(ocr_results.keys()) | set(tag_results.keys())
        combined_scores = {}
        
        for photo_id in all_photo_ids:
            score = 0.0
            if photo_id in ocr_results:
                score += float(ocr_results[photo_id])
            if photo_id in tag_results:
                score += float(tag_results[photo_id])
            combined_scores[photo_id] = score
        
        # Filter by date and state
        photo_ids_to_check = list(combined_scores.keys())
        
        photos_query = session.query(Photo.id).filter(
            Photo.id.in_(photo_ids_to_check),
            Photo.state == PhotoState.COMPLETED
        )
        
        if date_from:
            photos_query = photos_query.filter(Photo.created_at >= date_from)
        if date_to:
            photos_query = photos_query.filter(Photo.created_at <= date_to)
        
        valid_photo_ids = {pid[0] for pid in photos_query.all()}
        
        # Filter results to only valid photos
        filtered_scores = {
            photo_id: score
            for photo_id, score in combined_scores.items()
            if photo_id in valid_photo_ids
        }
        
        # Sort by score and limit
        sorted_results = sorted(
            filtered_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        logger.info(f"Keyword search found {len(sorted_results)} results")
        return sorted_results
        
    except Exception as e:
        logger.error(f"Keyword search error: {e}")
        return []


def semantic_search(
    session: Session,
    query: str,
    limit: int = 100,
    categories: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Tuple[int, float]]:
    """
    Perform semantic vector search using OpenCLIP embeddings.
    
    Args:
        session: Database session
        query: Search query string
        limit: Maximum number of results
        categories: Optional list of category names to filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        
    Returns:
        List of (photo_id, distance) sorted by similarity (lower distance = more similar)
    """
    try:
        # Generate query embedding
        query_embedding = ai_models.generate_text_embedding(query)
        
        # Build base query for vector similarity search
        embedding_query = session.query(
            SemanticEmbedding.photo_id,
            SemanticEmbedding.embedding.cosine_distance(query_embedding).label('distance')
        ).join(Photo, SemanticEmbedding.photo_id == Photo.id).filter(
            Photo.state == PhotoState.COMPLETED
        )
        
        # Apply date filters
        if date_from:
            embedding_query = embedding_query.filter(Photo.created_at >= date_from)
        if date_to:
            embedding_query = embedding_query.filter(Photo.created_at <= date_to)
        
        # Apply category filter
        if categories:
            category_ids = session.query(Category.id).filter(
                Category.name.in_(categories)
            ).all()
            category_ids = [cid[0] for cid in category_ids]
            
            if category_ids:
                # Filter photos that have detected objects in these categories
                photo_ids_in_categories = session.query(DetectedObject.photo_id).filter(
                    DetectedObject.category_id.in_(category_ids)
                ).distinct().all()
                photo_ids_in_categories = [pid[0] for pid in photo_ids_in_categories]
                
                embedding_query = embedding_query.filter(
                    SemanticEmbedding.photo_id.in_(photo_ids_in_categories)
                )
        
        # Order by distance and limit
        results = embedding_query.order_by('distance').limit(limit).all()
        
        logger.info(f"Semantic search found {len(results)} results")
        return [(photo_id, float(distance)) for photo_id, distance in results]
        
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return []


def hybrid_search(
    query: str,
    mode: str = 'hybrid',
    categories: Optional[List[str]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    show_duplicates: bool = True,
    page: int = 1,
    page_size: int = 50
) -> Dict:
    """
    Perform hybrid search combining keyword and semantic vector search with RRF fusion.
    
    Args:
        query: Search query string
        mode: Search mode ('hybrid', 'keyword', or 'semantic')
        categories: Optional list of category names to filter
        date_from: Optional start date filter
        date_to: Optional end date filter
        show_duplicates: Whether to include duplicate photos
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Dict with search results and metadata
    """
    session = get_session()
    
    try:
        # Perform searches based on mode
        if mode == 'keyword':
            keyword_results = keyword_search(
                session, query, settings.SEARCH_TOP_K,
                categories, date_from, date_to
            )
            final_results = keyword_results
            
        elif mode == 'semantic':
            semantic_results = semantic_search(
                session, query, settings.SEARCH_TOP_K,
                categories, date_from, date_to
            )
            final_results = semantic_results
            
        else:  # hybrid mode
            keyword_results = keyword_search(
                session, query, settings.SEARCH_TOP_K,
                categories, date_from, date_to
            )
            semantic_results = semantic_search(
                session, query, settings.SEARCH_TOP_K,
                categories, date_from, date_to
            )
            
            # Apply RRF fusion
            final_results = reciprocal_rank_fusion(
                keyword_results,
                semantic_results,
                k=settings.RRF_K
            )
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_photo_ids = [photo_id for photo_id, _ in final_results[start_idx:end_idx]]
        
        # Fetch photo details
        photos = session.query(Photo).filter(Photo.id.in_(paginated_photo_ids)).all()
        
        # Create results with metadata
        results = []
        for photo in photos:
            # Get matched tags
            matched_tags = session.query(DetectedObject.tag).filter(
                DetectedObject.photo_id == photo.id
            ).limit(5).all()
            matched_tags = [tag[0] for tag in matched_tags]
            
            # Get OCR snippet if available
            ocr_text = session.query(OCRText.extracted_text).filter(
                OCRText.photo_id == photo.id
            ).first()
            ocr_snippet = ocr_text[0][:200] + "..." if ocr_text and ocr_text[0] else None
            
            # Get score for this photo
            score = next((score for pid, score in final_results if pid == photo.id), 0.0)
            
            results.append({
                'photo': photo,
                'score': score,
                'matched_tags': matched_tags,
                'ocr_snippet': ocr_snippet
            })
        
        return {
            'results': results,
            'total': len(final_results),
            'page': page,
            'page_size': page_size,
            'mode': mode
        }
        
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        return {
            'results': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'mode': mode,
            'error': str(e)
        }
        
    finally:
        session.close()


def get_photo_details(photo_id: int) -> Optional[Dict]:
    """
    Get detailed information about a photo.
    
    Args:
        photo_id: Photo ID
        
    Returns:
        Dict with photo details or None if not found
    """
    session = get_session()
    
    try:
        photo = session.query(Photo).filter_by(id=photo_id).first()
        
        if not photo:
            return None
        
        # Get detected objects
        objects = session.query(DetectedObject).filter_by(photo_id=photo_id).all()
        
        # Get OCR text
        ocr = session.query(OCRText).filter_by(photo_id=photo_id).first()
        
        # Get faces count
        from models import Face
        faces_count = session.query(Face).filter_by(photo_id=photo_id).count()
        
        # Check for duplicates
        from models import Duplicate
        has_duplicates = session.query(Duplicate).filter(
            or_(
                Duplicate.photo_id_1 == photo_id,
                Duplicate.photo_id_2 == photo_id
            )
        ).count() > 0
        
        return {
            'photo': photo,
            'detected_objects': objects,
            'ocr_text': ocr.extracted_text if ocr else None,
            'faces_count': faces_count,
            'has_duplicates': has_duplicates
        }
        
    finally:
        session.close()

