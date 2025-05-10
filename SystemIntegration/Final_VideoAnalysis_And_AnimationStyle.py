import os
import shutil
import cv2
import whisper
import yt_dlp
import librosa
import numpy as np
import subprocess
import joblib
from moviepy.editor import VideoFileClip, AudioFileClip
from flask import Flask, request, jsonify
from flask_cors import CORS

from train_model import extract_advanced_features  # make sure this exists

# ========== Flask Setup ==========
notebook_app = Flask("notebook_receiver")
CORS(notebook_app)

# ========== Environment ==========
os.environ["IMAGEIO_FFMPEG_EXE"] = shutil.which("ffmpeg")

# ========== Delete ==========
def delete_temp_files():
    files_to_delete = ["full_video.mp4", "style_clip.mp4", "audio.wav"]
    for file in files_to_delete:
        try:
            os.remove(file)
            print(f"Deleted: {file}")
        except FileNotFoundError:
            print(f"File not found (already deleted or missing): {file}")
        except PermissionError as pe:
            print(f"Permission denied when deleting {file}: {pe}")
        except Exception as e:
            print(f"Unexpected error deleting {file}: {e}")


# ========== Download & Processing ==========
def download_youtube_video(url, output_path="full_video.mp4"):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'merge_output_format': 'mp4',
        'ffmpeg_location': shutil.which("ffmpeg")
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

def extract_audio(video_path, output_path="audio.wav"):
    command = f"ffmpeg -i {video_path} -q:a 0 -map a {output_path} -y"
    subprocess.run(command, shell=True)
    return output_path

def analyze_speech(audio_path):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)
    total_words = sum(len(seg['words']) for seg in result['segments'])
    speech_duration = sum(word['end'] - word['start'] for seg in result['segments'] for word in seg['words'])
    total_duration = AudioFileClip(audio_path).duration
    speech_percent = (speech_duration / total_duration) * 100
    wpm = (total_words / (speech_duration / 60)) if speech_duration > 0 else 0
    adjusted_wpm = wpm * (speech_percent / 100)

    if adjusted_wpm <= 50:
        level = 'Low'
    elif adjusted_wpm <= 100:
        level = 'Moderate'
    else:
        level = 'High'

    return level, total_words, adjusted_wpm

def analyze_music(audio_path, segment_length=5, rms_threshold=0.02, contrast_threshold=20):
    y, sr = librosa.load(audio_path, sr=None)
    total_duration = librosa.get_duration(y=y, sr=sr)
    music_time = 0

    for start in range(0, int(total_duration), segment_length):
        end = min(start + segment_length, int(total_duration))
        segment = y[int(start * sr): int(end * sr)]
        rms = np.mean(librosa.feature.rms(y=segment))
        contrast = np.mean(librosa.feature.spectral_contrast(y=segment, sr=sr))
        if rms > rms_threshold and contrast > contrast_threshold:
            music_time += segment_length

    percentage = (music_time / total_duration) * 100
    if percentage <= 20:
        return 'Low', percentage
    elif percentage <= 40:
        return 'Moderate', percentage
    else:
        return 'High', percentage

def analyze_scene_changes(video_path, threshold=30):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_minutes = (total_frames / fps) / 60
    scene_changes = 0
    prev_frame = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            if np.mean(cv2.absdiff(prev_frame, gray)) > threshold:
                scene_changes += 1
        prev_frame = gray
    cap.release()

    changes_per_minute = scene_changes / duration_minutes
    if changes_per_minute < 10:
        return 'Low', scene_changes, changes_per_minute
    elif changes_per_minute < 30:
        return 'Moderate', scene_changes, changes_per_minute
    else:
        return 'High', scene_changes, changes_per_minute

def predict_video_style(video_path):
    model = joblib.load("style_model.pkl")
    le = joblib.load("label_encoder.pkl")
    features = extract_advanced_features(video_path)
    if not features:
        return "Unknown"
    preds = model.predict(features)
    labels = le.inverse_transform(preds)
    return max(set(labels), key=list(labels).count)

def determine_final_stimulation(speech, music, scene):
    matrix = {
        ('Low', 'Low', 'Low'): 'Low Stimulation',
        ('Low', 'Low', 'Moderate'): 'Low Stimulation',
        ('Low', 'Moderate', 'Low'): 'Low Stimulation',
        ('Moderate', 'Low', 'Low'): 'Low Stimulation',

        # Moderate
        ('Low', 'Low', 'High'): 'Moderate Stimulation',
        ('Low', 'Moderate', 'Moderate'): 'Moderate Stimulation',
        ('Low', 'High', 'Low'): 'Moderate Stimulation',
        ('Low', 'High', 'Moderate'): 'Moderate Stimulation',
        ('Moderate', 'Low', 'Moderate'): 'Moderate Stimulation',
        ('Moderate', 'Moderate', 'Low'): 'Moderate Stimulation',
        ('Moderate', 'Low', 'High'): 'Moderate Stimulation',
        ('High', 'Low', 'Low'): 'Moderate Stimulation',
        ('High', 'Low', 'Moderate'): 'Moderate Stimulation',
        ('Moderate', 'High', 'Low'): 'Moderate Stimulation',
        ('High', 'Moderate', 'Low'): 'Moderate Stimulation',

        # High
        ('Low', 'Moderate', 'High'): 'High Stimulation',
        ('Low', 'High', 'High'): 'High Stimulation',
        ('Moderate', 'Moderate', 'Moderate'): 'High Stimulation',
        ('Moderate', 'Moderate', 'High'): 'High Stimulation',
        ('Moderate', 'High', 'Moderate'): 'High Stimulation',
        ('Moderate', 'High', 'High'): 'High Stimulation',
        ('High', 'Moderate', 'Moderate'): 'High Stimulation',
        ('High', 'Moderate', 'High'): 'High Stimulation',
        ('High', 'High', 'Low'): 'High Stimulation',
        ('High', 'High', 'Moderate'): 'High Stimulation',
        ('High', 'High', 'High'): 'High Stimulation',
        ('High', 'Low', 'High'): 'High Stimulation'
    }
    return matrix.get((speech, music, scene), "Unknown")

# ========== Main Pipeline ==========
def analyze_video_pipeline(youtube_url):
    video_path = download_youtube_video(youtube_url)
    audio_path = extract_audio(video_path)
    scene_level, scene_changes, changes_per_min = analyze_scene_changes(video_path)

    # Trim for style analysis only
    temp_clip = VideoFileClip(video_path).subclip(0, 60)
    temp_clip.write_videofile("style_clip.mp4", codec='libx264', audio_codec='aac', verbose=False, logger=None)
    temp_clip.close()

    animation_style = predict_video_style("style_clip.mp4")
    speech_level, words, wpm = analyze_speech(audio_path)
    music_level, music_percent = analyze_music(audio_path)
    final_stim = determine_final_stimulation(speech_level, music_level, scene_level)

    os.remove(video_path)
    os.remove("style_clip.mp4")
    return {
        "speech_level": speech_level,
        "music_level": music_level,
        "scene_level": scene_level,
        "animation_style": animation_style,
        "final_stimulation": final_stim
    }

# ========== Flask Route ==========
@notebook_app.route("/receive_video", methods=["POST"])
def receive_video():
    data = request.get_json()
    video_url = data.get("video_url")
    user_email = data.get("email")  # You need to receive this from the extension!
    channel_name = data.get("channel_name", "Unknown Channel")
    youtube_title = data.get("video_title", "عنوان غير معروف")

    print(f"Received URL from extension: {video_url}")
    print(f"For User: {user_email}")

    try:
        result = analyze_video_pipeline(video_url)
        
        if not result:
            raise ValueError("Analysis result is None")

        # Extract values BEFORE using them
        stimulation_level = result["final_stimulation"]
        animation_style = result["animation_style"]
        speech_level = result["speech_level"]
        music_level = result["music_level"]
        scene_level = result["scene_level"]
        
        # Optional cluster logic
        cluster_map = {
            "2D Cartoon (Flat Colors)": 0,
            "3D CGI (Shadows, Bright)": 1,
            "Live Action (Real Humans)": 2
        }
        cluster_id = cluster_map.get(animation_style, -1)

        # INSERT into database
        import sqlite3
        conn = sqlite3.connect("tranquileye.db")
        cursor = conn.cursor()
        # Define action_taken based on stimulation_level
        if "high" in stimulation_level.lower():
            action_taken = "إعادة توجيه"
        elif ("medium" in stimulation_level.lower() or 
            "low" in stimulation_level.lower() or 
            "moderate" in stimulation_level.lower()):
            action_taken = "استمرار بالمشاهدة"
        else:
            action_taken = "غير محدد"

        cursor.execute('''
        INSERT INTO report (email, channel_name, youtube_title, youtube_url, stimulation_level, action_taken)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
        user_email,
        channel_name,
        youtube_title,
        video_url,
        stimulation_level,
        action_taken
        ))

        conn.commit()
        conn.close()

        delete_temp_files()

        return jsonify({
            "received": True,
            "video_url": video_url,
            "analysis": {
                "speech": speech_level,
                "music": music_level,
                "scene": scene_level,
                "animation_style": animation_style,
                "final_stimulation": stimulation_level,
                #"cluster": cluster_id
            }
        })

     # Specific Exceptions
    except yt_dlp.utils.DownloadError as de:
        return jsonify({"error": "YouTube download failed", "details": str(de)}), 502

    except subprocess.SubprocessError as se:
        return jsonify({"error": "FFmpeg processing error", "details": str(se)}), 500

    except sqlite3.DatabaseError as db_err:
        return jsonify({"error": "Database error", "details": str(db_err)}), 500

    except ValueError as ve:
        return jsonify({"error": "Invalid data encountered", "details": str(ve)}), 400

    # Final generic exception (fail-safe)
    except Exception as e:
        return jsonify({"error": "Unexpected server error", "details": str(e)}), 500


# ========== Run Flask ==========
if __name__ == "__main__":
    notebook_app.run(port=8890)
