
import sqlite3
import pandas as pd

df = pd.read_csv("TranquilEye_SceneFrequency_Standardized.csv")
print(df.columns.tolist())


conn = sqlite3.connect('tranquileye.db')
cursor = conn.cursor()

# USER TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  password TEXT NOT NULL
)
''')

# CHANNEL TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS channel (
  channel_name TEXT PRIMARY KEY,
  stimulation_level TEXT
)
''')

# WATCHES TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS watches (
  email TEXT,
  channel_name TEXT,
  PRIMARY KEY (email, channel_name),
  FOREIGN KEY (email) REFERENCES user(email) ON DELETE CASCADE,
  FOREIGN KEY (channel_name) REFERENCES channel(channel_name) ON DELETE CASCADE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS report (
  reportID INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT,                            -- للربط الخلفي فقط
  channel_name TEXT,
  youtube_title TEXT,
  youtube_url TEXT,
  stimulation_level TEXT,
  action_taken TEXT,
  FOREIGN KEY (email) REFERENCES user(email) ON DELETE CASCADE,
  FOREIGN KEY (channel_name) REFERENCES channel(channel_name) ON DELETE CASCADE
)
''')

# Create the program_data table*
# Create the program_data table*
cursor.execute('''
CREATE TABLE IF NOT EXISTS program_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program TEXT,
    stimulation_level TEXT,
    animation_style TEXT,
    scene_frequency TEXT,
    speech_level TEXT,
    music_level TEXT
)
''')

# Insert data from CSV*
# Normalize CSV column names
df.columns = [col.strip().lower().replace(" ", "_").replace("-", "_") for col in df.columns]


# Insert data from CSV safely
for _, row in df.iterrows():
    program = str(row["programs"]).strip().lower()
    stimulation_level = str(row["stimulation_level"]).strip().lower()
    animation_style = str(row["animation_styles"]).strip().lower()
    scene_frequency = str(row["scene_frequency"]).strip().lower()
    speech_level = str(row["dialogue_intensity"]).strip().lower()
    music_level = str(row["total_music_time"]).strip().lower()  # <-- updated key

    # Avoid duplicates
    cursor.execute("SELECT COUNT(*) FROM program_data WHERE program = ?", (program,))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO program_data 
            (program, stimulation_level, animation_style, scene_frequency, speech_level, music_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (program, stimulation_level, animation_style, scene_frequency, speech_level, music_level))




conn.commit()
conn.close()

print("✅ All tables created successfully in tranquileye.db.")
print("✅ CSV data imported to program_data table.")
