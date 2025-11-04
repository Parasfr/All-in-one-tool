print("This tool only reset Gmail hotmail and aol domain for another domains check my Pass reset bot option 5th")
import requests
import json

def rst(username_or_email):
    url = "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"
    
    session = requests.Session()
    session.get('https://www.instagram.com/accounts/password/reset/')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.instagram.com/accounts/password/reset/',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-IG-App-ID': '936619743392459',
        'X-CSRFToken': session.cookies.get('csrftoken', '')
    }

    data = {'email_or_username': username_or_email}

    try:
        response = session.post(url, headers=headers, data=data)
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))

if __name__ == "__main__":
    username = input("Username/email: ")
    rst(username)



    
