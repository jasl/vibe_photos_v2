import importlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class _SQLText(str):
    def __new__(cls, value: str):
        obj = str.__new__(cls, value)
        obj.text = value
        return obj


sqlalchemy_stub = types.ModuleType("sqlalchemy")
sqlalchemy_stub.text = lambda value: _SQLText(value)
sys.modules.setdefault("sqlalchemy", sqlalchemy_stub)
sys.modules.setdefault("sqlalchemy.orm", types.ModuleType("sqlalchemy.orm"))


celery_stub = types.ModuleType("celery")
celery_stub.Task = type("Task", (), {})
sys.modules.setdefault("celery", celery_stub)


config_stub = types.ModuleType("config")
config_stub.settings = types.SimpleNamespace(OCR_LANG="ch", LOG_LEVEL="INFO")
config_stub.Settings = type("Settings", (), {})
sys.modules.setdefault("config", config_stub)


workers_stub = types.ModuleType("workers")
workers_stub.__path__ = []  # Mark as package
sys.modules.setdefault("workers", workers_stub)


celery_app_stub = types.ModuleType("workers.celery_app")


class _DummyCeleryApp:
    def task(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


celery_app_stub.app = _DummyCeleryApp()
sys.modules.setdefault("workers.celery_app", celery_app_stub)
workers_stub.celery_app = celery_app_stub


ai_models_stub = types.ModuleType("workers.ai_models")
ai_models_stub.extract_text = lambda *args, **kwargs: None
ai_models_stub.initialize_models = lambda: None
ai_models_stub.recognize_objects = lambda *args, **kwargs: []
ai_models_stub.generate_image_embedding = lambda *args, **kwargs: []
ai_models_stub.detect_faces = lambda *args, **kwargs: []
sys.modules.setdefault("workers.ai_models", ai_models_stub)
workers_stub.ai_models = ai_models_stub


models_stub = types.ModuleType("models")


class _Stub:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _PhotoState:
    PREPROCESSING = types.SimpleNamespace(value="preprocessing")
    PROCESSING_OBJECTS = types.SimpleNamespace(value="processing_objects")
    PROCESSING_EMBEDDINGS = types.SimpleNamespace(value="processing_embeddings")
    PROCESSING_OCR = types.SimpleNamespace(value="processing_ocr")
    PROCESSING_FACES = types.SimpleNamespace(value="processing_faces")
    PROCESSING_HASH = types.SimpleNamespace(value="processing_hash")
    CHECKING_DUPLICATES = types.SimpleNamespace(value="checking_duplicates")
    COMPLETED = types.SimpleNamespace(value="completed")
    PARTIAL = types.SimpleNamespace(value="partial")
    FAILED = types.SimpleNamespace(value="failed")


class _OCRText:
    def __init__(self, photo_id: int, extracted_text: str, language: str):
        self.photo_id = photo_id
        self.extracted_text = extracted_text
        self.language = language


models_stub.Photo = _Stub
models_stub.DetectedObject = _Stub
models_stub.PhotoTag = _Stub
models_stub.SemanticEmbedding = _Stub
models_stub.OCRText = _OCRText
models_stub.Face = _Stub
models_stub.PhotoHash = _Stub
models_stub.Duplicate = _Stub
models_stub.TagCategoryMapping = _Stub
models_stub.PhotoState = _PhotoState
models_stub.get_session = lambda: None
sys.modules.setdefault("models", models_stub)


utils_stub = types.ModuleType("utils")


class _ImageConversionError(Exception):
    pass


def _dummy_process_image_for_storage(_path):
    return {}


utils_stub.ImageConversionError = _ImageConversionError
utils_stub.process_image_for_storage = _dummy_process_image_for_storage
sys.modules.setdefault("utils", utils_stub)


tasks_spec = importlib.util.spec_from_file_location(
    "workers.tasks", Path(__file__).resolve().parents[1] / "workers" / "tasks.py"
)
tasks = importlib.util.module_from_spec(tasks_spec)
sys.modules["workers.tasks"] = tasks
tasks_spec.loader.exec_module(tasks)
tasks.settings = config_stub.settings


class OCRLanguageTests(unittest.TestCase):
    def setUp(self):
        self.original_lang = tasks.settings.OCR_LANG

    def tearDown(self):
        tasks.settings.OCR_LANG = self.original_lang

    def test_store_ocr_text_english_uses_english_config(self):
        session = MagicMock()

        record = tasks._store_ocr_text(session, photo_id=42, extracted_text="Hello world", language_code="en")

        self.assertEqual(record.language, "en")
        session.flush.assert_called_once()
        session.execute.assert_called_once()
        args, kwargs = session.execute.call_args
        self.assertIn("to_tsvector", str(args[0]))
        params = args[1]
        self.assertEqual(params["config"], "english")
        self.assertEqual(params["photo_id"], 42)
        self.assertEqual(params["text"], "Hello world")
        session.commit.assert_called_once()

    def test_store_ocr_text_chinese_falls_back_to_simple_config(self):
        session = MagicMock()

        record = tasks._store_ocr_text(session, photo_id=7, extracted_text="你好 世界", language_code="ch")

        self.assertEqual(record.language, "ch")
        session.flush.assert_called_once()
        session.execute.assert_called_once()
        args, kwargs = session.execute.call_args
        self.assertIn("to_tsvector", str(args[0]))
        params = args[1]
        self.assertEqual(params["config"], "simple")
        self.assertEqual(params["photo_id"], 7)
        self.assertEqual(params["text"], "你好 世界")
        session.commit.assert_called_once()

    @patch("workers.tasks._store_ocr_text")
    @patch("workers.tasks.ai_models.extract_text", return_value="Sample text")
    def test_process_ocr_uses_current_language_setting(self, extract_mock, store_mock):
        tasks.settings.OCR_LANG = "ch"
        session = MagicMock()
        photo = MagicMock()
        photo.id = 101
        results = {"steps_completed": []}

        tasks._process_ocr(session, photo, "dummy.png", results)

        store_mock.assert_called_once_with(session, photo.id, "Sample text", "ch")
        self.assertIn("ocr", results["steps_completed"])
        self.assertEqual(results["ocr_text_length"], len("Sample text"))
        extract_mock.assert_called_once_with("dummy.png")


if __name__ == "__main__":
    unittest.main()
