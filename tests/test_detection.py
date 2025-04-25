import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app
from app.core.config import settings

client = TestClient(app)

# Helper: Get id_token from Firebase REST API (reuse from test_auth.py if needed)
FIREBASE_EMAIL = "tester@email.com"
FIREBASE_PASSWORD = "568303"
FIREBASE_API_KEY = "AIzaSyCihN1jBnbMocE3kcW4is_H6_cqpeFzWqA"

def get_id_token(email, password, api_key):
    import requests
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["idToken"]

@pytest.fixture(scope="module")
def test_image_path():
    img_path = os.path.join(os.path.dirname(__file__), "test.jpg")
    if not os.path.exists(img_path):
        pytest.skip("Chưa có file tests/test.jpg để test emotion detection. Hãy thêm file ảnh vào tests/test.jpg!")
    return img_path

@pytest.fixture(scope="module")
def auth_token():
    if FIREBASE_EMAIL and FIREBASE_PASSWORD and FIREBASE_API_KEY:
        return get_id_token(FIREBASE_EMAIL, FIREBASE_PASSWORD, FIREBASE_API_KEY)
    pytest.skip("Chưa thiết lập thông tin tài khoản Firebase test!")

def test_detect_emotion_guest(test_image_path):
    # Guest user detect (no token)
    with open(test_image_path, "rb") as f:
        files = {"file": ("test.jpg", f, "image/jpeg")}
        resp = client.post("/api/detect", files=files)
    assert resp.status_code in [200, status.HTTP_403_FORBIDDEN]
    if resp.status_code == 200:
        data = resp.json()
        assert "detection_id" in data
        assert "detection_results" in data
        assert data["user_id"].startswith("guest_")
        # New: check multi-face structure
        dr = data["detection_results"]
        assert "faces" in dr
        assert isinstance(dr["faces"], list)
        if dr["faces"]:
            face = dr["faces"][0]
            assert "box" in face
            assert "emotions" in face
            assert isinstance(face["emotions"], list)

def test_detect_emotion_authenticated(test_image_path, auth_token):
    # Authenticated user detect
    with open(test_image_path, "rb") as f:
        files = {"file": ("test.jpg", f, "image/jpeg")}
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = client.post("/api/detect", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "detection_id" in data
    assert "detection_results" in data
    assert data["user_id"] != ""
    # New: check multi-face structure
    dr = data["detection_results"]
    assert "faces" in dr
    assert isinstance(dr["faces"], list)
    if dr["faces"]:
        face = dr["faces"][0]
        assert "box" in face
        assert "emotions" in face
        assert isinstance(face["emotions"], list)

    # Save detection_id for later tests
    global DETECTION_ID
    DETECTION_ID = data["detection_id"]

def test_get_history_authenticated(auth_token):
    # Get detection history for authenticated user
    headers = {"Authorization": f"Bearer {auth_token}"}
    resp = client.get("/api/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "detection_id" in data[0]
        global DETECTION_ID
        DETECTION_ID = data[0]["detection_id"]

def test_get_detection_detail_authenticated(auth_token):
    # Get detail of a detection
    headers = {"Authorization": f"Bearer {auth_token}"}
    detection_id = globals().get("DETECTION_ID", None)
    if not detection_id:
        pytest.skip("Không có detection_id để test chi tiết.")
    resp = client.get(f"/api/history/{detection_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["detection_id"] == detection_id

def test_delete_detection_authenticated(auth_token):
    # Delete a detection
    headers = {"Authorization": f"Bearer {auth_token}"}
    detection_id = globals().get("DETECTION_ID", None)
    if not detection_id:
        pytest.skip("Không có detection_id để test xóa.")
    resp = client.delete(f"/api/history/{detection_id}", headers=headers)
    assert resp.status_code == 204