import requests
import time

def test_api_receive_video():
    url = "http://127.0.0.1:8890/receive_video"
    payload = {
        "video_url": "https://youtu.be/8F8Iub8mB4M?si=hRHtgp6HncCP3BA-",
        "email": "sarazaitooni@gmail.com",
        "channel_name": "ShiningStarsluv",
        "video_title": "Name of Fruits Can you guess the Fruits Challenge 40 Fruits Name"
    }
    start = time.time()
    response = requests.post(url, json=payload)
    end = time.time()
    return round(end - start, 2), response.status_code

def test_extension_log_existing():
    url = "http://127.0.0.1:5005/log_existing_video"
    payload = {
        "email": "sarazaitooni@gmail.com",
        "channel_name": "Cocomelon",
        "youtube_title": "Wheels on the Bus",
        "youtube_url": "https://youtu.be/existing456",
        "stimulation_level": "high",
        "action_taken": "إعادة توجيه"
    }
    start = time.time()
    response = requests.post(url, json=payload)
    end = time.time()
    return round(end - start, 2), response.status_code

def test_dashboard_load():
    url = "http://127.0.0.1:5005/dashboard"
    start = time.time()
    response = requests.get(url)
    end = time.time()
    return round(end - start, 2), response.status_code

# Run all tests
print("Running performance tests...\n")

api_time, api_status = test_api_receive_video()
ext_time, ext_status = test_extension_log_existing()
dash_time, dash_status = test_dashboard_load()

# Output summary
print("Performance Summary:")
print(f"Flask API (/receive_video): {api_time}s  → {'PASS' if api_status == 200 else 'FAIL'}")
print(f"Extension (/log_existing_video): {ext_time}s  → {'PASS' if ext_status == 200 else 'FAIL'}")
print(f"Dashboard (/dashboard): {dash_time}s  → {'PASS' if dash_status == 200 else 'FAIL'}")
