import requests


FIREBASE_EMAIL="tester@email.com"
FIREBASE_PASSWORD="568303"
FIREBASE_API_KEY="AIzaSyCihN1jBnbMocE3kcW4is_H6_cqpeFzWqA"

# Hàm lấy id_token từ Firebase REST API
def get_id_token(email, password, api_key):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["idToken"]
  
# main
def main():
    # Lấy id_token từ Firebase
    token = get_id_token(FIREBASE_EMAIL, FIREBASE_PASSWORD, FIREBASE_API_KEY)
    print(f"ID Token: {token}")

if __name__ == "__main__":
    main()