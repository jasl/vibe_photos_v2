"""Helper utilities for filtering noisy object detections before persistence."""

from typing import Dict, List, Optional, Tuple

from config import settings


def compute_area_ratio(bbox: Optional[Dict], image_width: int, image_height: int) -> Optional[float]:
    """Compute the proportion of the image occupied by a bounding box."""
    if not bbox or image_width <= 0 or image_height <= 0:
        return None

    # Support both DETR-style (x1, y1, x2, y2) and width/height style bboxes
    if {'x1', 'y1', 'x2', 'y2'} <= bbox.keys():
        x1 = float(bbox.get('x1', 0))
        y1 = float(bbox.get('y1', 0))
        x2 = float(bbox.get('x2', 0))
        y2 = float(bbox.get('y2', 0))
    elif {'x', 'y', 'width', 'height'} <= bbox.keys():
        x1 = float(bbox.get('x', 0))
        y1 = float(bbox.get('y', 0))
        x2 = x1 + float(bbox.get('width', 0))
        y2 = y1 + float(bbox.get('height', 0))
    else:
        return None

    # Clamp to image boundaries and ensure non-negative sizes
    x1 = max(0.0, min(float(image_width), x1))
    y1 = max(0.0, min(float(image_height), y1))
    x2 = max(0.0, min(float(image_width), x2))
    y2 = max(0.0, min(float(image_height), y2))

    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)

    if width == 0 or height == 0:
        return 0.0

    image_area = float(image_width) * float(image_height)
    if image_area <= 0:
        return None

    return (width * height) / image_area


def filter_detected_objects(
    detected_objects: List[Dict],
    image_width: int,
    image_height: int
) -> Tuple[List[Dict], int]:
    """
    Filter noisy detections (e.g., background people) based on area/confidence thresholds.

    Returns filtered detections (with area_ratio annotated) and count of filtered objects.
    """
    noisy_tags = {tag.lower() for tag in settings.NOISY_DETECTION_TAGS}
    filtered_objects: List[Dict] = []
    filtered_out_count = 0
    noisy_buckets: Dict[str, List[Dict]] = {}

    for obj in detected_objects:
        annotated_obj = dict(obj)
        annotated_obj['area_ratio'] = compute_area_ratio(
            obj.get('bbox'), image_width, image_height
        )

        tag_lower = annotated_obj.get('tag', '').lower()
        if tag_lower in noisy_tags:
            area_ratio = annotated_obj.get('area_ratio')
            if area_ratio is not None and area_ratio < settings.NOISY_TAG_MIN_AREA_RATIO:
                filtered_out_count += 1
                continue
            if annotated_obj.get('confidence', 0.0) < settings.NOISY_TAG_MIN_CONFIDENCE:
                filtered_out_count += 1
                continue

            noisy_buckets.setdefault(tag_lower, []).append(annotated_obj)
        else:
            filtered_objects.append(annotated_obj)

    max_instances = settings.NOISY_TAG_MAX_INSTANCES
    limit_noisy_instances = max_instances > 0

    for bucket_objects in noisy_buckets.values():
        bucket_objects.sort(
            key=lambda item: (item.get('confidence', 0.0), item.get('area_ratio') or 0.0),
            reverse=True
        )
        if limit_noisy_instances:
            filtered_objects.extend(bucket_objects[:max_instances])
            filtered_out_count += max(0, len(bucket_objects) - max_instances)
        else:
            filtered_objects.extend(bucket_objects)

    return filtered_objects, filtered_out_count


__all__ = [
    "compute_area_ratio",
    "filter_detected_objects",
]
