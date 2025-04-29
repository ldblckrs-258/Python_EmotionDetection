# app/services/notification.py
"""
Simple notification system for background processing.
This can be extended to use WebSocket, email, or polling.
"""
from typing import Dict
from datetime import datetime, timedelta

# In-memory notification store with timestamps
# Store format: {detection_id: (status, timestamp)}
notification_store: Dict[str, tuple] = {}

def cleanup_old_notifications():
    """Remove notifications older than 5 minutes"""
    current_time = datetime.now()
    expired_ids = [
        detection_id for detection_id, (_, timestamp) in notification_store.items()
        if current_time - timestamp > timedelta(minutes=5)
    ]
    for detection_id in expired_ids:
        notification_store.pop(detection_id, None)

def set_notification(detection_id: str, status: str):
    cleanup_old_notifications()
    notification_store[detection_id] = (status, datetime.now())

def get_notification(detection_id: str) -> str:
    cleanup_old_notifications()
    notification_data = notification_store.get(detection_id)
    return notification_data[0] if notification_data else "done"

def notify_processing_done(detection_id: str):
    set_notification(detection_id, "done")

def notify_processing_failed(detection_id: str):
    set_notification(detection_id, "failed")
