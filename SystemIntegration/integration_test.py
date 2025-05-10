import unittest
import sqlite3
import time
import requests
from app import app

# 🔎 Fetch video title and channel from YouTube API
def fetch_youtube_metadata(video_id, api_key):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    if data["items"]:
        snippet = data["items"][0]["snippet"]
        return snippet["title"], snippet["channelTitle"]
    return None, None

class TestTranquilEyeFullFlow(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Clean test user
        conn = sqlite3.connect('tranquileye.db')
        conn.execute("DELETE FROM user WHERE email = 'sarazaitooni@gmail.com'")
        conn.execute("INSERT INTO user (email, name, password) VALUES (?, ?, ?)",
                     ('sarazaitooni@gmail.com', 'Sara Zaitooni', 'TestPass123'))
        conn.commit()
        conn.close()

    def test_known_video_dataset_flow(self):
        # Step 1: Log in
        self.client.post('/login', data={
            'email': 'sarazaitooni@gmail.com',
            'password': 'TestPass123'
        }, follow_redirects=True)

        # Step 2: Query known dataset video
        query_response = self.client.post('/get_program_data', json={"query": "cocomelon"})
        self.assertEqual(query_response.status_code, 200)
        program_info = query_response.get_json()

        # Step 3: Log to DB
        log_response = self.client.post('/log_existing_video', json={
            "channel_name": program_info['program'],
            "youtube_title": program_info['program'],
            "youtube_url": "https://youtu.be/e_04ZrNroTo",
            "stimulation_level": program_info['stimulation_level'],
            "action_taken": "إعادة توجيه" if "high" in program_info['stimulation_level'].lower() else "استمرار بالمشاهدة"
        })
        self.assertEqual(log_response.status_code, 200)
        self.assertIn("success", log_response.json['status'])

        # Step 4: Check dashboard
        dashboard = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn(program_info['program'], dashboard.data.decode('utf-8'))

    def test_unknown_video_analysis_with_metadata_fetch(self):
        # Step 1: Log in
        self.client.post('/login', data={
            'email': 'sarazaitooni@gmail.com',
            'password': 'TestPass123'
        }, follow_redirects=True)

        # Step 2: Fetch title/channel from YouTube API
        video_id = "MsW5fxmMl9A"
        api_key = "AIzaSyDzRaUaAojHpcyGfN8Vid9RkIkw89_pZRU" 
        video_title, channel_name = fetch_youtube_metadata(video_id, api_key)

        assert video_title and channel_name, "Failed to fetch metadata"

        # Step 3: Send to analyzer
        response = requests.post("http://127.0.0.1:8890/receive_video", json={
            "video_url": f"https://youtu.be/{video_id}",
            "email": "sarazaitooni@gmail.com",
            "video_title": video_title,
            "channel_name": channel_name
        }, timeout=180)
        assert response.status_code == 200
        assert "analysis" in response.json()

        # Step 4: Wait, then check dashboard
        time.sleep(5)
        dashboard = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn(video_title, dashboard.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
