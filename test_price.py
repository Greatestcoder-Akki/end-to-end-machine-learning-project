import requests
session = requests.Session()
login_data = {'phone': '0000', 'password': 'admin'}
session.post('http://127.0.0.1:5001/login', data=login_data)
res = session.post('http://127.0.0.1:5001/api/get-price-recommendation', json={'crop_name': 'Rice', 'grade': 'A'})
print(res.status_code)
if res.status_code != 200:
    print(res.text)
else:
    print(res.json())
