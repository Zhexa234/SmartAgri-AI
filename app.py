from flask import Flask, render_template, request, redirect, session
import pandas as pd
import numpy as np
import pickle
import os
import requests
import random
import smtplib
from email.mime.text import MIMEText
import time
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split

# CLASSIFICATION METRICS
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay
)

# REGRESSION METRICS
from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
    mean_squared_error
)

app = Flask(__name__)
app.secret_key = "agri_secret"
EMAIL_ADDRESS = "aismartagri@gmail.com"
EMAIL_PASSWORD = "vkfimjwbekunwxpr"
DB_PATH = "database/users.xlsx"


# -----------------------
# Filter datasets to get valid options for dropdowns
# -----------------------
yield_dataset = pd.read_csv(
    "datasets/crop_yield.csv"
)
fert_dataset = pd.read_csv(
    "datasets/fertilizer.csv"
)

# -----------------------
# Filter and strip datasets to ensure clean dropdown options
# -----------------------
yield_dataset.columns = yield_dataset.columns.str.strip()

yield_dataset['State_Name'] = (
    yield_dataset['State_Name']
    .astype(str)
    .str.strip()
)

yield_dataset['Season'] = (
    yield_dataset['Season']
    .astype(str)
    .str.strip()
)

yield_dataset['Crop'] = (
    yield_dataset['Crop']
    .astype(str)
    .str.strip()
)

# -----------------------
# mapping for dependent dropdowns
# -----------------------

soil_crop_map = {}

for soil in fert_dataset['Soil Type'].unique():

    crops = fert_dataset[
        fert_dataset['Soil Type'] == soil
    ]['Crop Type'].unique().tolist()

    soil_crop_map[soil] = crops
state_season_crop_map = {}

state_season_crop_map = {}

state_season_crop_map = {}

for _, row in yield_dataset.iterrows():

    state = row['State_Name']
    season = row['Season']
    crop = row['Crop']

    if state not in state_season_crop_map:
        state_season_crop_map[state] = {}

    if season not in state_season_crop_map[state]:
        state_season_crop_map[state][season] = []

    if crop not in state_season_crop_map[state][season]:
        state_season_crop_map[state][season].append(crop)


# -----------------------
# GLOBAL USAGE TRACKING
# -----------------------
yield_count = 0
fert_count = 0


# -----------------------
# INPUT RANGES
# -----------------------

RANGES = {
    "temperature": (0, 50),
    "humidity": (0, 100),
    "moisture": (0, 100),
    "nitrogen": (0, 150),
    "potassium": (0, 150),
    "phosphorous": (0, 150),
    "area": (0.1, 10000)
}

# -----------------------
# LOAD USERS
# -----------------------
def load_users():
    if os.path.exists(DB_PATH):
        return pd.read_excel(DB_PATH)
    else:
        df = pd.DataFrame(columns=["username","email","password","role"])
        df.to_excel(DB_PATH,index=False)
        return df

def save_users(df):
    df.to_excel(DB_PATH,index=False)

# -----------------------
# LOAD MODELS
# -----------------------
yield_model = pickle.load(open("models/yield_model.pkl","rb"))
le_state, le_season, le_crop = pickle.load(open("models/yield_encoder.pkl","rb"))

fert_model = pickle.load(open("models/fert_model.pkl","rb"))
le_soil, le_crop2, le_fert = pickle.load(open("models/fert_encoder.pkl","rb"))

# -----------------------
# SAFE ENCODER
# -----------------------
def safe_transform(le, val):
    val = val.strip()
    if val in le.classes_:
        return le.transform([val])[0]
    return 0


# -----------------------
# OTP SYSTEM (for future use in password reset or 2FA)
# -----------------------
def send_otp(email, otp):

    msg = MIMEText(f"""
SmartAgri AI Verification

Your OTP is: {otp}
Do not share this OTP.
""")

    msg['Subject'] = "SmartAgri OTP Verification"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# -----------------------
# OTP VERIFICATION PAGE (for future use)
# -----------------------
@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():

    if request.method == 'POST':

        entered_otp = request.form['otp']

        if entered_otp == session.get('otp'):

            data = session.get('temp_user')
            users = load_users()

            new_user = pd.DataFrame({
                "username":[data['username']],
                "email":[data['email']],
                "password":[data['password']],
                "role":["user"]
            })

            users = pd.concat([users, new_user], ignore_index=True)
            save_users(users)

            # CLEAR SESSION
            session.pop('otp', None)
            session.pop('temp_user', None)

            return redirect('/login')

        return render_template("otp_verify.html", error="Invalid OTP")

    return render_template("otp_verify.html")

# ======================
# RESEND OTP (for future use)
# ======================
@app.route('/resend_otp')
def resend_otp():

    if 'temp_user' not in session:
        return redirect('/signup')

    # 60 sec restriction
    if time.time() - session.get('otp_time', 0) < 60:
        return "Wait 60 seconds before retry"

    otp = str(random.randint(100000, 999999))

    session['otp'] = otp
    session['otp_time'] = time.time()

    send_otp(session['temp_user']['email'], otp)

    return redirect('/verify_otp')


# ======================
# AUTH SYSTEM
# ======================

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        users = load_users()

        user = users[
            (users['email']==email) &
            (users['password']==password)
        ]

        if not user.empty:

            role = user.iloc[0]['role']

            # ❌ BLOCK ADMIN FROM NORMAL LOGIN
            if role == "admin":
                return render_template("login.html", error="Use Admin Login")

            session['user'] = email
            session['role'] = "user"

            return redirect('/dashboard')

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")

# -----------------------
# ADMIN LOGIN
# -----------------------

@app.route('/admin_login', methods=['GET','POST'])
def admin_login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        users = load_users()

        user = users[
            (users['email']==email) &
            (users['password']==password) &
            (users['role']=="admin")
        ]

        if not user.empty:

            session['user'] = email
            session['role'] = "admin"

            return redirect('/admin')

        return render_template("admin_login.html", error="Not authorized")

    return render_template("admin_login.html")

# -----------------------
# SIGNUP
# -----------------------

@app.route('/signup', methods=['GET','POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        # CAPTCHA
        captcha_response = request.form.get('g-recaptcha-response')

        if not captcha_response:
            return render_template("signup.html", error="Complete captcha")

        secret_key = "6LcC1s8sAAAAAJ1Cb06LDptgz1dPOKowbsrNNRRM"

        verify = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={'secret': secret_key, 'response': captcha_response}
        ).json()

        if not verify.get("success"):
            return render_template("signup.html", error="Captcha failed")

        users = load_users()

        # USER CHECK
        if email in users['email'].values:
            return render_template("signup.html", error="Email already exists")

        if username in users['username'].values:
            return render_template("signup.html", error="Username already taken")

        # OTP GENERATION
        otp = str(random.randint(100000, 999999))

        session['temp_user'] = {
            "username": username,
            "email": email,
            "password": password
        }

        session['otp'] = otp
        session['otp_time'] = time.time()

        send_otp(email, otp)

        return redirect('/verify_otp')

    return render_template("signup.html")
# -----------------------
# LOGOUT
# -----------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ======================
# DASHBOARD
# ======================

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    return render_template("index.html")

# ======================
# YIELD
# ======================

@app.route('/yield')
def yield_page():

    if 'user' not in session:
        return redirect('/login')

    return render_template(
        "yield.html",
        states=le_state.classes_,
        seasons=le_season.classes_,
        crops=le_crop.classes_,
        ranges=RANGES,
        state_crop_map=state_season_crop_map
    )


@app.route('/predict_yield', methods=['POST'])
def predict_yield():

    global yield_count
    yield_count += 1

    if 'user' not in session:
        return redirect('/login')

    try:

        # FORM DATA
        state = safe_transform(le_state, request.form['state'])
        season = safe_transform(le_season, request.form['season'])
        crop = safe_transform(le_crop, request.form['crop'])
        area = float(request.form['area'])

        # PREDICTION
        pred = yield_model.predict([
            [state, season, crop, area]
        ])[0]

        # SAVE HISTORY
        history = load_history()

        new_row = pd.DataFrame({
            "user": [session['user']],
            "type": ["Yield"],
            "input": [
                f"{request.form['state']}, "
                f"{request.form['crop']}, "
                f"{area}"
            ],
            "result": [round(pred, 2)]
        })

        history = pd.concat(
            [history, new_row],
            ignore_index=True
        )

        save_history(history)

        # RETURN RESULT
        return render_template(
            "yield.html",
            prediction=round(pred, 2),
            confidence=95,
            states=le_state.classes_,
            seasons=le_season.classes_,
            crops=le_crop.classes_,
            ranges=RANGES,
            state_crop_map=state_season_crop_map
        )

    except Exception as e:
        return f"Error: {e}"
# ======================
# FERTILIZER
# ======================

@app.route('/fertilizer')
def fertilizer():

    if 'user' not in session:
        return redirect('/login')

    return render_template(
        "fertilizer.html",
        soils=le_soil.classes_,
        crops=le_crop2.classes_,
        ranges=RANGES,
        soil_crop_map=soil_crop_map
    )


@app.route('/predict_fertilizer', methods=['POST'])
def predict_fertilizer():

    global fert_count
    fert_count += 1

    if 'user' not in session:
        return redirect('/login')

    try:

        # FORM DATA
        temperature = float(request.form['temperature'])
        humidity = float(request.form['humidity'])
        moisture = float(request.form['moisture'])

        soil = safe_transform(
            le_soil,
            request.form['soil']
        )

        crop = safe_transform(
            le_crop2,
            request.form['crop']
        )

        nitrogen = float(request.form['nitrogen'])
        potassium = float(request.form['potassium'])
        phosphorous = float(request.form['phosphorous'])

        # MODEL INPUT
        data = [[
            temperature,
            humidity,
            moisture,
            soil,
            crop,
            nitrogen,
            potassium,
            phosphorous
        ]]

        # PREDICTION
        pred = fert_model.predict(data)

        raw_result = le_fert.inverse_transform(pred)[0]

        # FRIENDLY FERTILIZER NAMES
        fertilizer_map = {

            "17-17-17":
            "NPK Balanced Fertilizer",

            "14-35-14":
            "DAP (High Phosphorus)",

            "28-28":
            "DAP Fertilizer",

            "20-20":
            "Balanced NPK Fertilizer",

            "6-6-6":
            "Low Strength NPK Fertilizer",

            "10-26-26":
            "Potassium Rich Fertilizer",

            "Urea":
            "Urea (High Nitrogen Fertilizer)"
        }

        result = fertilizer_map.get(
            raw_result,
            raw_result
        )

        # SAVE HISTORY
        history = load_history()

        new_row = pd.DataFrame({

            "user": [session['user']],

            "type": ["Fertilizer"],

            "input": [
                f"{request.form['crop']}, "
                f"{request.form['soil']}"
            ],

            "result": [result]

        })

        history = pd.concat(
            [history, new_row],
            ignore_index=True
        )

        save_history(history)

        # RETURN RESULT
        return render_template(
            "fertilizer.html",
            result=result,
            soils=le_soil.classes_,
            crops=le_crop2.classes_,
            ranges=RANGES,
            soil_crop_map=soil_crop_map
        )

    except Exception as e:
        return f"Error: {e}"
# -----------------------
# CHARTS
# -----------------------
@app.route('/charts')
def charts():

    if 'user' not in session:
        return redirect('/login')

    history = load_history()

    yield_usage = len(history[history['type'] == "Yield"])
    fert_usage = len(history[history['type'] == "Fertilizer"])

    return render_template(
        "charts.html",
        yield_usage=yield_usage,
        fert_usage=fert_usage
    )

# -----------------------
# ADMIN PAGE
# -----------------------
@app.route('/admin')
def admin():

    if 'user' not in session or session.get('role') != 'admin':
        return redirect('/admin_login')

    users = load_users()
    history = load_history()

    # ✅ Get REAL counts from history (Excel)
    yield_total = len(history[history['type'] == "Yield"])
    fert_total = len(history[history['type'] == "Fertilizer"])

    return render_template(
        "admin.html",
        users=users.to_dict(orient="records"),
        total_users=len(users),
        total_predictions=len(history),
        yield_count=yield_total,
        fert_count=fert_total
    )
# -----------------------
# HISTORY STORAGE and DB
# -----------------------

HISTORY_PATH = "database/history.xlsx"

def load_history():
    if os.path.exists(HISTORY_PATH):
        return pd.read_excel(HISTORY_PATH)
    else:
        df = pd.DataFrame(columns=[
            "user","type","input","result"
        ])
        df.to_excel(HISTORY_PATH, index=False)
        return df

def save_history(df):
    df.to_excel(HISTORY_PATH, index=False)


@app.route('/history')
def history():

    if 'user' not in session:
        return redirect('/login')

    data = load_history()

    # 👇 ROLE-BASED VIEW
    if session.get('role') == 'admin':
        # Admin sees ALL data
        records = data.to_dict(orient="records")
    else:
        # User sees only their data
        user_data = data[data['user'] == session['user']]
        records = user_data.to_dict(orient="records")

    return render_template("history.html", records=records)


# -----------------------
# add or delete users (admin only)
# -----------------------

@app.route('/add_user', methods=['POST'])
def add_user():

    if 'user' not in session or session.get('role') != 'admin':
        return redirect('/admin_login')

    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    users = load_users()

    # Prevent duplicate email
    if email in users['email'].values:
        return redirect('/admin')

    new_user = pd.DataFrame({
        "username":[username],
        "email":[email],
        "password":[password],
        "role":[role]
    })

    users = pd.concat([users, new_user], ignore_index=True)
    save_users(users)

    return redirect('/admin')


@app.route('/delete_user/<email>')
def delete_user(email):

    if 'user' not in session or session.get('role') != 'admin':
        return redirect('/admin_login')

    users = load_users()

    users = users[users['email'] != email]

    save_users(users)

    return redirect('/admin')

# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(debug=True)