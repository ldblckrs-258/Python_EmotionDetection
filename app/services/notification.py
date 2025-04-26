# app/services/notification.py
"""
Simple notification system for background processing.
This can be extended to use WebSocket, email, or polling.
"""
import threading
from typing import Dict

# In-memory notification store (for demo, should use Redis or DB in production)
notification_store: Dict[str, str] = {}

def set_notification(detection_id: str, status: str):
    notification_store[detection_id] = status

def get_notification(detection_id: str) -> str:
    return notification_store.get(detection_id, "pending")

def notify_processing_done(detection_id: str):
    set_notification(detection_id, "done")

def notify_processing_failed(detection_id: str):
    set_notification(detection_id, "failed")
