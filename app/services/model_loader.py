import threading
from transformers import AutoImageProcessor, AutoModelForImageClassification
from app.core.config import settings

# Thread-safe singleton cache for model and processor
class EmotionModelCache:
    _lock = threading.Lock()
    _model = None
    _processor = None

    @classmethod
    def get_model_and_processor(cls):
        with cls._lock:
            if cls._model is None or cls._processor is None:
                print(f"[ModelLoader] Loading model: {settings.HUGGINGFACE_MODEL}")
                cls._processor = AutoImageProcessor.from_pretrained(settings.HUGGINGFACE_MODEL, use_fast=True)
                cls._model = AutoModelForImageClassification.from_pretrained(settings.HUGGINGFACE_MODEL)
                print("[ModelLoader] Model loaded successfully")
            return cls._processor, cls._model
