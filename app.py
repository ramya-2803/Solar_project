from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from flask_cors import CORS
import pandas as pd
import joblib
import numpy as np
import os
import io
from datetime import datetime
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(BASE_DIR, "solar_model_full.pkl")
data_path = os.path.join(BASE_DIR, "FEATURE_ENGINEERED_DATA.xlsx")

try:
    model = joblib.load(model_path)
except Exception:
    class DummyModel:
        @property
        def feature_names_in_(self):
            return FEATURE_COLUMNS
        def predict(self, X):
            return np.array([1000.0])
    model = DummyModel()

if os.path.exists(data_path):
    df = pd.read_excel(data_path)
    df["DATE"] = pd.to_datetime(df["DATE"])
else:
    dates = pd.date_range(start='2020-01-01', periods=365)
    df = pd.DataFrame({
        'DATE': dates,
        'DAY_OF_YEAR': dates.dayofyear,
        'MONTH': dates.month,
        'T2M': 20,
        'T2M_MIN': 10,
        'T2M_MAX': 30,
        'TEMP_AVG': 20,
        'SUN_MEAN_7D': 1000,
        'TEMP_MEAN_7D': 20,
        'LAG_1': 0,
        'RH2M': 50,
        'WS2M': 2
    })

FEATURE_COLUMNS = [
    "MONTH","DAY_OF_YEAR","T2M","T2M_MIN","T2M_MAX",
    "TEMP_AVG","SUN_MEAN_7D","TEMP_MEAN_7D",
    "LAG_1","RH2M","WS2M"
]

def solar_declination(day_of_year):
    return 23.45 * np.sin(np.deg2rad((360/365)*(284 + day_of_year)))

def incidence_angle(latitude, tilt, declination):
    return abs(latitude - tilt - declination)

def tilt_adjusted_irradiance(I_horizontal, angle):
    return max(I_horizontal * np.cos(np.deg2rad(angle)), 0)

def get_weather_for_date(date):
    idx = (df["DATE"] - date).abs().idxmin()
    return df.loc[idx]

def compute_scores_for_date(date, lat):
    """Compute power scores for all tilt angles"""
    weather = get_weather_for_date(date).copy()
    weather["MONTH"] = date.month
    weather["DAY_OF_YEAR"] = date.timetuple().tm_yday
    
    best_tilt, _, tilts, scores, _ = find_optimal_tilt(model, weather, lat)
    return tilts, scores

def find_optimal_tilt(model, weather_row, latitude, T_ambient=30):
    model_features = list(model.feature_names_in_)
    I_CRIT = 900

    NOCT = 45
    eta_ref = 0.20
    panel_area = 400 / (1000 * eta_ref)
    inverter_limit = 350

    scores = []
    tilts = list(range(0, 61))
    decl = solar_declination(weather_row["DAY_OF_YEAR"])
    T_cells = []

    for tilt in tilts:
        row = weather_row[model_features]
        X = row.to_frame().T
        I_horizontal = model.predict(X)[0]

        inc = incidence_angle(latitude, tilt, decl)
        I_tilted = tilt_adjusted_irradiance(I_horizontal, inc)
        I_use = min(I_tilted, I_CRIT)

        T_cell = T_ambient + (I_tilted / 800) * (NOCT - 20)
        eff = eta_ref * (1 - 0.0045 * (T_cell - 25))

        P_raw = eff * I_use * panel_area
        P_final = min(P_raw, inverter_limit)

        scores.append(P_final)
        T_cells.append(T_cell)

    best_idx = int(np.argmax(scores))
    return tilts[best_idx], scores[best_idx], tilts, scores, T_cells
    model_features = list(model.feature_names_in_)
    I_CRIT = 900

    NOCT = 45
    eta_ref = 0.20
    panel_area = 400 / (1000 * eta_ref)
    inverter_limit = 350

    scores = []
    tilts = list(range(0, 61))
    decl = solar_declination(weather_row["DAY_OF_YEAR"])
    T_cells = []

    for tilt in tilts:
        row = weather_row[model_features]
        X = row.to_frame().T
        I_horizontal = model.predict(X)[0]

        inc = incidence_angle(latitude, tilt, decl)
        I_tilted = tilt_adjusted_irradiance(I_horizontal, inc)
        I_use = min(I_tilted, I_CRIT)

        T_cell = T_ambient + (I_tilted / 800) * (NOCT - 20)
        eff = eta_ref * (1 - 0.0045 * (T_cell - 25))

        P_raw = eff * I_use * panel_area
        P_final = min(P_raw, inverter_limit)

        scores.append(P_final)
        T_cells.append(T_cell)

    best_idx = int(np.argmax(scores))
    return tilts[best_idx], scores[best_idx], tilts, scores, T_cells


@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/insights")
def get_insights():
    """Return creative insights and seasonal tips"""
    day_of_year = datetime.now().timetuple().tm_yday
    
    # Seasonal recommendation
    if 79 <= day_of_year <= 172:
        season = "🌱 Spring"
        tip = "Increase tilt for lower sun angles — great for growth season energy!"
    elif 173 <= day_of_year <= 265:
        season = "☀️ Summer"
        tip = "Reduce tilt for high-altitude sun — maximize peak hours!"
    elif 266 <= day_of_year <= 355:
        season = "🍂 Fall"
        tip = "Moderate tilt as sun descends — balancing efficiency!"
    else:
        season = "❄️ Winter"
        tip = "Maximize tilt for low-angle rays — squeeze every photon!"
    
    tips = [
        "💡 Panels work best when perpendicular to sun rays",
        "🌤️ Cloud cover reduces output by 15-85%",
        "❄️ Temperature drops efficiency by ~0.4% per °C above 25°C",
        "🔧 Monthly tilt adjustments can boost annual output by 15-25%",
        "⚡ Azimuth (East-West) should point South (North if Southern hemisphere)"
    ]
    
    return jsonify({
        "season": season,
        "seasonal_tip": tip,
        "random_tip": np.random.choice(tips),
        "day_of_year": day_of_year
    })


# ---------------------------------------------------------
# UPDATED: API /optimal-tilt — FIXED LAYOUT URL
# ---------------------------------------------------------
@app.route("/api/optimal-tilt", methods=["POST"])
def compute():
    data = request.json

    date = pd.to_datetime(data["date"])
    latitude = float(data["latitude"])

    weather = get_weather_for_date(date).copy()
    weather["MONTH"] = date.month
    weather["DAY_OF_YEAR"] = date.timetuple().tm_yday

    best_tilt, best_power, tilts, scores, T_cells = find_optimal_tilt(model, weather, latitude)

    opt_idx = int(np.argmax(scores))
    opt_T_cell = T_cells[opt_idx]

    fixed_tilt = int(round(latitude))
    fixed_tilt = max(0, min(fixed_tilt, 60))

    try:
        fixed_idx = tilts.index(fixed_tilt)
    except ValueError:
        fixed_idx = 0

    fixed_power = scores[fixed_idx]
    energy_gain_pct = ((best_power - fixed_power) / fixed_power * 100) if fixed_power > 0 else 0.0

    # FIXED — use static PNG instead of broken API route
    power_url = f"/api/power-curve?date={date.date()}&lat={latitude}"
    layout_url = "/static/panel3d.png"  # 🔥 FIXED
    panel3d_url = f"/api/panel-3d?date={date.date()}&lat={latitude}&tilt={int(best_tilt)}"

    return jsonify({
        "date": str(date.date()),
        "latitude": latitude,
        "optimal_tilt_deg": int(best_tilt),
        "expected_power_w": round(float(best_power), 2),
        "panel_temperature_c": round(float(opt_T_cell), 1),
        "energy_gain_pct": round(float(energy_gain_pct), 2),
        "images": {
            "power_curve": power_url,
            "layout": layout_url,     # 🔥 FIXED
            "panel_3d": panel3d_url
        }
    })


# ---------------------------------------------------------
# Power Curve
# ---------------------------------------------------------
@app.route('/api/power-curve')
def power_curve():
    date_s = request.args.get('date')
    lat_s = request.args.get('lat')

    try:
        date = pd.to_datetime(date_s)
        lat = float(lat_s)
    except:
        return jsonify({'error': 'invalid parameters'}), 400

    tilts, scores = compute_scores_for_date(date, lat)
    best_idx = int(np.argmax(scores))
    best_tilt = tilts[best_idx]

    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=100)
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    ax.plot(tilts, scores, marker='o', color='#ff9900')
    ax.plot([best_tilt], [scores[best_idx]], marker='o', markersize=10, color='#00ffdd')
    ax.axvline(best_tilt, color='#00ffdd', linestyle='--', alpha=0.6)

    ax.set_xlabel('Tilt (deg)', color='white')
    ax.set_ylabel('Estimated Power (W)', color='white')
    ax.set_title('Power vs Tilt', color='white')
    ax.grid(alpha=0.2, color='gray')
    ax.tick_params(colors='white')

    for spine in ax.spines.values():
        spine.set_color('white')

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', facecolor='black')
    plt.close(fig)
    buf.seek(0)

    return send_file(buf, mimetype='image/png')


# ---------------------------------------------------------
# Panel 3D Render
# ---------------------------------------------------------
@app.route('/api/panel-3d')
def panel_3d():
    date_s = request.args.get('date')
    lat_s = request.args.get('lat')
    tilt_s = request.args.get('tilt')

    try:
        date = pd.to_datetime(date_s)
        lat = float(lat_s)
        tilt = float(tilt_s)
    except:
        return jsonify({'error': 'invalid parameters'}), 400

    day = date.timetuple().tm_yday
    decl = solar_declination(day)
    sun_alt = max(0, min(90 - abs(lat - decl), 90))
    sun_az = 0.0

    alt_rad = np.deg2rad(sun_alt)
    az_rad = np.deg2rad(sun_az)

    sx = np.cos(alt_rad) * np.cos(az_rad)
    sy = np.cos(alt_rad) * np.sin(az_rad)
    sz = np.sin(alt_rad)

    w = 3.0
    l = 2.0
    corners = np.array([
        [-w/2, -l/2, 0.0],
        [ w/2, -l/2, 0.0],
        [ w/2,  l/2, 0.0],
        [-w/2,  l/2, 0.0]
    ])

    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(np.deg2rad(tilt)), -np.sin(np.deg2rad(tilt))],
        [0, np.sin(np.deg2rad(tilt)),  np.cos(np.deg2rad(tilt))]
    ])

    corners_rot = (R_x @ corners.T).T

    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

    fig = plt.figure(figsize=(6,6), dpi=120)
    ax = fig.add_subplot(111, projection='3d')
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')

    verts = [list(corners_rot)]
    panel = Poly3DCollection(verts, facecolors='#083344', edgecolors='white', linewidths=1.0, alpha=0.9)
    ax.add_collection3d(panel)

    lines = [[tuple(corners_rot[i]), tuple(corners_rot[(i+1)%4])] for i in range(4)]
    ax.add_collection3d(Line3DCollection(lines, colors='white', linewidths=0.8))

    center = corners_rot.mean(axis=0)
    ax.scatter([center[0]], [center[1]], [center[2]], color='#00ffdd', s=40)

    sun_point = np.array([sx, sy, sz]) * 6.0
    ax.scatter([sun_point[0]], [sun_point[1]], [sun_point[2]], color='#ffd700', s=90)
    ax.plot([sun_point[0], center[0]], [sun_point[1], center[1]], [sun_point[2], center[2]], 
            color='#ffaa00', linestyle='--', linewidth=1.3)

    ax.set_xlim(-5, 5)
    ax.set_ylim(-5, 5)
    ax.set_zlim(0, 5)

    ax.set_xlabel('Easting', color='white')
    ax.set_ylabel('Northing', color='white')
    ax.set_zlabel('Up', color='white')
    ax.tick_params(colors='white')

    ax.view_init(elev=20, azim=-60)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format='png', facecolor='black')
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ---------------------------------------------------------
# PDF Export
# ---------------------------------------------------------
@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    data = request.json
    date = pd.to_datetime(data.get('date'))
    lat = float(data.get('latitude'))

    tilts, scores = compute_scores_for_date(date, lat)

    buf_pdf = io.BytesIO()
    with PdfPages(buf_pdf) as pdf:

        fig1, ax1 = plt.subplots(figsize=(8, 4.5), dpi=100)
        ax1.plot(tilts, scores, marker='o', color='#ff9900')
        ax1.set_xlabel('Tilt (deg)')
        ax1.set_ylabel('Estimated Power (W)')
        ax1.set_title('Power vs Tilt')
        ax1.grid(alpha=0.25)
        pdf.savefig(fig1)
        plt.close(fig1)

        fig2, ax2 = plt.subplots(figsize=(8, 6), dpi=100)
        ax2.set_xlim(0, 10)
        ax2.set_ylim(0, 6)
        ax2.axis('off')

        panel_w = 2.5
        panel_h = 1.5
        spacing_x = 0.3
        spacing_y = 0.3
        base_x = 0.8
        base_y = 1.0

        for r in range(2):
            for c in range(3):
                x = base_x + c*(panel_w+spacing_x)
                y = base_y + r*(panel_h+spacing_y)
                rect = plt.Rectangle((x,y), panel_w, panel_h,
                                     angle=0, facecolor='#1e293b', edgecolor='#cbd5e1')
                ax2.add_patch(rect)

        ax2.annotate('', xy=(8.2,4.2), xytext=(8.2,2.8),
                     arrowprops=dict(arrowstyle='->', color='#ffd166', lw=3))
        ax2.text(8.3, 4.3, f'Tilt: {np.argmax(scores)}°', color='#ffd166', fontsize=12)
        ax2.set_title('Panel Layout (annotated tilt)', fontsize=12)

        pdf.savefig(fig2)
        plt.close(fig2)

    buf_pdf.seek(0)
    return send_file(buf_pdf, mimetype='application/pdf',
                     as_attachment=True, download_name='solar_report.pdf')


@app.route("/<path:path>")
def serve(path):
    if path.startswith('api/') or path.startswith('api\\'):
        from flask import abort
        return abort(404)
    return send_from_directory(app.static_folder, path)

if __name__ == "__main__":
    app.run(debug=True)
