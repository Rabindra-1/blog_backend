#!/usr/bin/env python
import requests
import json

def test_comment_api():
    print("=== Comment API Test ===\n")
    
    # First, get a valid user token by registering or logging in
    # For this test, we'll try to login with an existing user
    login_url = "http://127.0.0.1:8000/api/auth/login/"
    
    # Try to login with admin user (you might need to adjust credentials)
    login_data = {
        "username_or_email": "admin",
        "password": "admin123"  # Replace with actual password
    }
    
    try:
        login_response = requests.post(login_url, json=login_data)
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data['access']
            print("✅ Login successful, got token")
        else:
            print("❌ Login failed - you'll need to test with frontend")
            print(f"Login response: {login_response.status_code} - {login_response.text}")
            return
    except Exception as e:
        print(f"❌ Login request failed: {str(e)}")
        return
    
    # Test comment creation
    comment_url = "http://127.0.0.1:8000/api/comments/blog/8/"  # Blog ID 8
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    comment_data = {
        "content": "This is a test comment posted via HTTP API!"
    }
    
    try:
        comment_response = requests.post(comment_url, json=comment_data, headers=headers)
        print(f"Comment POST Status: {comment_response.status_code}")
        
        if comment_response.status_code == 201:
            print("✅ Comment posted successfully!")
            comment_result = comment_response.json()
            print(f"Comment ID: {comment_result.get('id')}")
            print(f"Content: {comment_result.get('content')}")
        else:
            print(f"❌ Comment posting failed: {comment_response.text}")
    
    except Exception as e:
        print(f"❌ Comment request failed: {str(e)}")
    
    # Test getting comments
    try:
        get_response = requests.get(comment_url)
        if get_response.status_code == 200:
            comments_data = get_response.json()
            print(f"\n✅ Retrieved comments successfully")
            print(f"Total comments: {comments_data.get('count', len(comments_data.get('results', [])))}")
        else:
            print(f"❌ Failed to retrieve comments: {get_response.status_code}")
    
    except Exception as e:
        print(f"❌ Get comments request failed: {str(e)}")

if __name__ == "__main__":
    test_comment_api()