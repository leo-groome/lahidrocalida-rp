
import requests
import json

def test_analytics():
    # Get token first
    login_url = "http://localhost:8000/auth/login-simple"
    login_payload = {"user_id": "3", "password": "admin123"}
    resp = requests.post(login_url, json=login_payload)
    token = resp.json()["access_token"]
    
    # Test analytics for Feb 2026
    url = "http://localhost:8000/admin/analytics?fecha_inicio=2026-02-01&fecha_fin=2026-02-28"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    print(f"Total Ventas Feb: {data['resumen']['total_ventas']}")
    print(f"Sample timeline entry: {data['timeline'][0] if data['timeline'] else 'Empty'}")
    
    # Test analytics for Mar 2026
    url = "http://localhost:8000/admin/analytics?fecha_inicio=2026-03-01&fecha_fin=2026-03-31"
    response = requests.get(url, headers=headers)
    data = response.json()
    print(f"Total Ventas Mar: {data['resumen']['total_ventas']}")

if __name__ == "__main__":
    test_analytics()
