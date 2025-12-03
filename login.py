import requests
from getpass import getpass

def authenticate(username, password):
    """
    Authenticate a user by sending credentials to a login API.
    
    Args:
        username (str): The user's username.
        password (str): The user's password.
        
    Returns:
        dict: A dictionary containing the response from the server.
    """
    url = "https://api.ryx-ai.com/login"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def login():
    """
    Prompt the user for their credentials and attempt to log them in.
    """
    username = input("Enter your username: ")
    password = getpass("Enter your password: ")
    
    result = authenticate(username, password)
    if result:
        print("Login successful!")
        # Handle successful login (e.g., store token, redirect user)
    else:
        print("Login failed. Please check your credentials.")

if __name__ == "__main__":
    login()