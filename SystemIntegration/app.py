from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
CORS(app)
app.secret_key = 'your_secret_key'  # Required for session and flash

# Connect to SQLite database
def connect_db():
    return sqlite3.connect('tranquileye.db')

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Dashboard (requires login)
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'email' not in session:
        flash("يرجى تسجيل الدخول أولاً.")
        return redirect(url_for('login'))

    user_email = session.get('email')

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reportID, channel_name, youtube_title, youtube_url, stimulation_level, action_taken
        FROM report
        WHERE email = ?
    ''', (user_email,))
    rows = cursor.fetchall()
    conn.close()

    reports = [
        {
            'reportID': row[0],
            'channel_name': row[1],
            'youtube_title': row[2],
            'youtube_url': row[3],
            'stimulation_level': row[4],
            'action_taken': row[5]
        }
        for row in rows
    ]

    return render_template('dashboard.html', reports=reports)

# Dashboard Delete Row
@app.route('/delete_report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM report WHERE reportID = ?", (report_id,))
    conn.commit()
    conn.close()
    flash("تم حذف التقرير بنجاح.")
    return redirect(url_for('dashboard'))


# Signup page (form + process)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirmPassword']

        if not email.endswith('@gmail.com'):
            flash("يجب استخدام بريد إلكتروني من Gmail فقط.")
            return redirect(url_for('signup'))

        # strong password checking
        import re

        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$'
        if not re.match(pattern, password):
            flash("كلمة المرور ضعيفة. يجب أن تحتوي على 8 أحرف على الأقل، حرف كبير، حرف صغير، ورقم.")
            return redirect(url_for('signup'))

        if password != confirm:
            flash("كلمات المرور غير متطابقة!")
            return redirect(url_for('signup'))

        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO user (email, name, password) VALUES (?, ?, ?)",
                           (email, name, password))
            conn.commit()
            flash("تم إنشاء الحساب بنجاح!")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("البريد الإلكتروني مستخدم بالفعل.")
            return redirect(url_for('signup'))
        finally:
            conn.close()

    return render_template('signup.html')

# Login page (form + process)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, password FROM user WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()

        if result:
            db_name, db_password = result
            if password == db_password:
                session['email'] = email
                session['name'] = db_name
                flash("تم تسجيل الدخول بنجاح")
                return redirect(url_for('dashboard'))
            else:
                flash("كلمة المرور غير صحيحة.")
        else:
            flash("لا يوجد حساب بهذا البريد الإلكتروني.")

        return redirect(url_for('login'))

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("تم تسجيل الخروج بنجاح.")
    return redirect(url_for('index'))

# Forgot Password page
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        flash("ميزة الاستعادة لم تُفعّل بعد.")  
        return redirect(url_for('forgot_password'))
    return render_template('forgot-password.html')


# Esraa
import requests  
#Dataset part *
@app.route("/get_program_data", methods=["POST"])
def get_program_data():
    import re
    data = request.get_json()
    query = data.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Missing query"}), 400

    words = re.findall(r"\b\w+\b", query)  # Split into words safely 

    conn = sqlite3.connect("tranquileye.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all potential matches using LIKE
    sql = "SELECT * FROM program_data WHERE " + " OR ".join(
        ["LOWER(program) LIKE ?" for _ in words]
    )
    values = [f"%{word}%" for word in words]

    cursor.execute(sql, values)
    rows = cursor.fetchall()
    conn.close()

    # Priority: exact word match first (e.g., "cocomelon" in "cocomelon")
    for row in rows:
        program = row["program"].lower()
        for word in words:
            if word == program or word in program:
                return jsonify(dict(row))

    # Fallback to best partial word (weighted match) , not sure for using
    """
    best_match = None
    best_score = 0
    for row in rows:
        program = row["program"].lower()
        score = sum(1 for word in words if word in program)
        if score > best_score:
            best_score = score
            best_match = row

    if best_match:
        return jsonify(dict(best_match))
    """
    return jsonify({"message": "Not found"}), 404


#new* detect animation style for redirecting
@app.route("/get_fallback_by_style", methods=["POST"])
def get_fallback_by_style():
    data = request.get_json()
    style = data.get("animation_style", "").strip().lower()

    if not style:
        return jsonify({"error": "Missing animation style"}), 400

    conn = sqlite3.connect("tranquileye.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM program_data
        WHERE LOWER(animation_style) = ?
        AND LOWER(stimulation_level) IN ("low stimulation", "moderate stimulation")
        ORDER BY RANDOM() LIMIT 1
    ''', (style,))
    
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify(dict(row))
    else:
        return jsonify({"message": "No fallback found"}), 404

# Analysis part
"""
import requests

@app.route("/analyze_video", methods=["POST"])
def analyze_video():
    data = request.get_json()
    video_url = data.get("video_url")
    user_email = session.get("email")

    if not video_url or not user_email:
        return jsonify({"error": "Missing video_url or user not logged in"}), 400

    try:
        response = requests.post(
            "http://localhost:8890/receive_video",
            json={"video_url": video_url, "email": user_email}
        )

        if response.status_code != 200:
            return jsonify({"error": "Analyzer service failed", "status_code": response.status_code}), 502

        return jsonify(response.json())

    # Specific exception for HTTP errors
    except requests.exceptions.RequestException as re:
        return jsonify({"error": "Connection to analyzer service failed", "details": str(re)}), 503

    # Specific exception for JSON parsing issues
    except ValueError as ve:
        return jsonify({"error": "Invalid JSON response from analyzer", "details": str(ve)}), 500

    # Final generic exception (fail-safe)
    except Exception as e:
        return jsonify({"error": "Unexpected server error", "details": str(e)}), 500
"""
# new >> Sara 
import sqlite3

@app.route('/log_existing_video', methods=['POST'])
def log_existing_video():
    data = request.get_json()
    print("Logging existing video:", data)

   # email = data.get('email')

    email = session.get("email")
    channel_name = data.get('channel_name')
    youtube_title = data.get('youtube_title')
    youtube_url = data.get('youtube_url')
    stimulation_level = data.get('stimulation_level')
    action_taken = data.get('action_taken')

    #if not all([email, channel_name, youtube_title, youtube_url, stimulation_level, action_taken]):
    if not all([channel_name, youtube_title, youtube_url, stimulation_level, action_taken]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        conn = sqlite3.connect('tranquileye.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO report (email, channel_name, youtube_title, youtube_url, stimulation_level, action_taken)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (email, channel_name, youtube_title, youtube_url, stimulation_level, action_taken))

        conn.commit()

        return jsonify({"status": "success", "message": "Existing video logged into report"})

    except sqlite3.IntegrityError as ie:
        return jsonify({"status": "error", "message": "Database integrity error", "details": str(ie)}), 409

    except sqlite3.OperationalError as oe:
        return jsonify({"status": "error", "message": "Database operational error", "details": str(oe)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Unexpected server error", "details": str(e)}), 500

    finally:
        conn.close()



# Use a different port to avoid conflict
if __name__ == '__main__':
    app.run(debug=True, port=5005)




