import unittest

from config import settings
from workers.object_filtering import filter_detected_objects


class FilterDetectedObjectsTestCase(unittest.TestCase):
    """Unit tests for filtering noisy object detections."""

    def setUp(self):
        # Preserve existing configuration so tests do not leak state
        self._original_tags = list(settings.NOISY_DETECTION_TAGS)
        self._original_min_area = settings.NOISY_TAG_MIN_AREA_RATIO
        self._original_min_confidence = settings.NOISY_TAG_MIN_CONFIDENCE
        self._original_max_instances = settings.NOISY_TAG_MAX_INSTANCES

        # Use deterministic thresholds for tests
        settings.NOISY_DETECTION_TAGS = ["person"]
        settings.NOISY_TAG_MIN_AREA_RATIO = 0.02
        settings.NOISY_TAG_MIN_CONFIDENCE = 0.1
        settings.NOISY_TAG_MAX_INSTANCES = 2

    def tearDown(self):
        settings.NOISY_DETECTION_TAGS = self._original_tags
        settings.NOISY_TAG_MIN_AREA_RATIO = self._original_min_area
        settings.NOISY_TAG_MIN_CONFIDENCE = self._original_min_confidence
        settings.NOISY_TAG_MAX_INSTANCES = self._original_max_instances

    def test_small_person_does_not_trigger_people_tag(self):
        """Background pedestrians with tiny area should be filtered out."""
        image_width, image_height = 1000, 1000
        detections = [
            {
                "tag": "person",
                "confidence": 0.95,
                "bbox": {"x1": 10, "y1": 10, "x2": 40, "y2": 40},  # 0.0009 area ratio
            },
            {
                "tag": "person",
                "confidence": 0.8,
                "bbox": {"x1": 50, "y1": 100, "x2": 650, "y2": 900},  # 0.36 area ratio
            },
        ]

        filtered, filtered_out = filter_detected_objects(detections, image_width, image_height)

        # Only the large subject should remain
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered_out, 1)
        self.assertEqual(filtered[0]["confidence"], 0.8)
        self.assertGreater(filtered[0]["area_ratio"], settings.NOISY_TAG_MIN_AREA_RATIO)

        # Simulate PhotoTag deduplication logic to ensure only one "person" tag exists
        unique_tags = {}
        for obj in filtered:
            tag = obj["tag"]
            if tag not in unique_tags or obj["confidence"] > unique_tags[tag]["confidence"]:
                unique_tags[tag] = obj

        self.assertIn("person", unique_tags)
        self.assertEqual(unique_tags["person"]["confidence"], 0.8)

    def test_only_small_persons_are_removed(self):
        """If only tiny pedestrians are detected, none should be kept."""
        image_width, image_height = 640, 480
        detections = [
            {
                "tag": "person",
                "confidence": 0.6,
                "bbox": {"x1": 0, "y1": 0, "x2": 20, "y2": 25},
            },
            {
                "tag": "person",
                "confidence": 0.55,
                "bbox": {"x1": 100, "y1": 150, "x2": 130, "y2": 180},
            },
        ]

        filtered, filtered_out = filter_detected_objects(detections, image_width, image_height)

        self.assertEqual(filtered, [])
        self.assertEqual(filtered_out, 2)


if __name__ == "__main__":
    unittest.main()
