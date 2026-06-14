import requests
session = requests.Session()
login_data = {'phone': '0000', 'password': 'admin'}
session.post('http://127.0.0.1:5001/login', data=login_data)
res = session.get('http://127.0.0.1:5001/marketplace')
print(res.status_code)
if res.status_code != 200:
    print(res.text)
