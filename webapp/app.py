"""
Flask web application for AI Photos Management.
Provides read-only gallery and hybrid search interface.
"""

import logging
from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path

from config import settings
from models import Photo, get_session, PhotoState, Category
from services import hybrid_search, get_photo_details

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.route('/')
def index():
    """Home page showing photo gallery."""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = settings.GALLERY_PAGE_SIZE
        
        session = get_session()
        
        # Get total count
        total_photos = session.query(Photo).filter(
            Photo.state == PhotoState.COMPLETED
        ).count()
        
        # Get paginated photos
        photos = session.query(Photo).filter(
            Photo.state == PhotoState.COMPLETED
        ).order_by(Photo.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        # Calculate pagination
        total_pages = (total_photos + page_size - 1) // page_size
        
        session.close()
        
        return render_template(
            'index.html',
            photos=photos,
            page=page,
            total_pages=total_pages,
            total_photos=total_photos
        )
        
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/search')
def search():
    """Search page with hybrid search."""
    try:
        query = request.args.get('q', '')
        mode = request.args.get('mode', 'hybrid')
        categories = request.args.getlist('category')
        page = request.args.get('page', 1, type=int)
        
        # Get available categories for filter
        session = get_session()
        all_categories = session.query(Category).all()
        session.close()
        
        results = None
        if query:
            # Perform search
            search_results = hybrid_search(
                query=query,
                mode=mode,
                categories=categories if categories else None,
                page=page,
                page_size=settings.GALLERY_PAGE_SIZE
            )
            results = search_results
        
        return render_template(
            'search.html',
            query=query,
            mode=mode,
            selected_categories=categories,
            all_categories=all_categories,
            results=results,
            page=page
        )
        
    except Exception as e:
        logger.error(f"Error in search route: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/photo/<int:photo_id>')
def photo_detail(photo_id):
    """Photo detail page."""
    try:
        details = get_photo_details(photo_id)
        
        if not details:
            return render_template('error.html', error='Photo not found'), 404
        
        return render_template('photo_detail.html', **details)
        
    except Exception as e:
        logger.error(f"Error in photo_detail route: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/thumbnail/<int:photo_id>')
def serve_thumbnail(photo_id):
    """Serve thumbnail image."""
    try:
        session = get_session()
        photo = session.query(Photo).filter_by(id=photo_id).first()
        session.close()
        
        if not photo or not photo.thumbnail_path:
            return "Thumbnail not found", 404
        
        thumbnail_path = Path(photo.thumbnail_path)
        if not thumbnail_path.exists():
            return "Thumbnail file not found", 404
        
        return send_file(thumbnail_path, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Error serving thumbnail: {e}")
        return "Error serving thumbnail", 500


@app.route('/api/stats')
def api_stats():
    """API endpoint for processing statistics."""
    try:
        session = get_session()
        
        # Count photos by state
        total = session.query(Photo).count()
        completed = session.query(Photo).filter(Photo.state == PhotoState.COMPLETED).count()
        pending = session.query(Photo).filter(Photo.state == PhotoState.PENDING).count()
        failed = session.query(Photo).filter(Photo.state == PhotoState.FAILED).count()
        partial = session.query(Photo).filter(Photo.state == PhotoState.PARTIAL).count()
        
        # Processing states
        processing_states = [
            PhotoState.PREPROCESSING,
            PhotoState.PROCESSING_OBJECTS,
            PhotoState.PROCESSING_EMBEDDINGS,
            PhotoState.PROCESSING_OCR,
            PhotoState.PROCESSING_FACES,
            PhotoState.PROCESSING_HASH,
            PhotoState.CHECKING_DUPLICATES
        ]
        processing = session.query(Photo).filter(Photo.state.in_(processing_states)).count()
        
        session.close()
        
        completion_percentage = (completed / total * 100) if total > 0 else 0
        
        return jsonify({
            'total_photos': total,
            'completed': completed,
            'pending': pending,
            'processing': processing,
            'partial': partial,
            'failed': failed,
            'completion_percentage': round(completion_percentage, 2)
        })
        
    except Exception as e:
        logger.error(f"Error in stats API: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
def api_search():
    """API endpoint for search (JSON response)."""
    try:
        query = request.args.get('q', '')
        mode = request.args.get('mode', 'hybrid')
        categories = request.args.getlist('category')
        page = request.args.get('page', 1, type=int)
        
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        search_results = hybrid_search(
            query=query,
            mode=mode,
            categories=categories if categories else None,
            page=page,
            page_size=settings.GALLERY_PAGE_SIZE
        )
        
        # Convert results to JSON-serializable format
        results_json = {
            'total': search_results['total'],
            'page': search_results['page'],
            'page_size': search_results['page_size'],
            'mode': search_results['mode'],
            'results': [
                {
                    'photo_id': result['photo'].id,
                    'filename': result['photo'].filename,
                    'score': result['score'],
                    'matched_tags': result['matched_tags'],
                    'ocr_snippet': result['ocr_snippet']
                }
                for result in search_results['results']
            ]
        }
        
        return jsonify(results_json)
        
    except Exception as e:
        logger.error(f"Error in search API: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Print configuration
    settings.print_config()
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.FLASK_DEBUG
    )

