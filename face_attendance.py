# ============================================================
#   SMSK - SMART FACE ATTENDANCE SYSTEM
#   Features: Face Recognition + Voice + Live Dashboard
# ============================================================

import cv2
import os
import csv
import threading
import webbrowser
import pyttsx3
from datetime import datetime
from deepface import DeepFace
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── College Settings ───────────────────────────────────────
COLLEGE_NAME    = "XYZ College of Engineering"
KNOWN_FACES_DIR = "known_faces"
ATTENDANCE_FILE = "attendance_records/attendance.csv"
DASHBOARD_PORT  = 5000

# ── Student Database ───────────────────────────────────────
STUDENT_DB = {
    "student1": ("Student 1", "CSE", "1001"),
    "student2": ("Student 2", "CSE", "1002"),
    "student3": ("Student 3", "ECE", "1003"),
    "student4": ("Student 4", "IT", "1004")
}

# ── Voice Setup ────────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)

def speak(text):
    def _speak():
        engine.say(text)
        engine.runAndWait()
    t = threading.Thread(target=_speak)
    t.daemon = True
    t.start()

# ── Dashboard HTML ─────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="5">
<title>SMSK Attendance Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',sans-serif; background:#0a0a1a; color:white; min-height:100vh; }
  .header { background:linear-gradient(135deg,#1a1a6e,#0d47a1); padding:20px 30px; display:flex; justify-content:space-between; align-items:center; border-bottom:3px solid #00e5ff; }
  .header h1 { font-size:1.6rem; letter-spacing:2px; }
  .header h1 span { color:#00e5ff; }
  .live-badge { background:#e53935; padding:6px 14px; border-radius:20px; font-size:0.8rem; font-weight:bold; animation:pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  .stats { display:flex; gap:20px; padding:20px 30px; background:#0d0d2b; }
  .stat-card { flex:1; background:linear-gradient(135deg,#1a237e,#283593); border-radius:12px; padding:18px; text-align:center; border:1px solid #3949ab; }
  .stat-card .number { font-size:2.5rem; font-weight:bold; color:#00e5ff; }
  .stat-card .label { font-size:0.8rem; color:#90caf9; margin-top:5px; letter-spacing:1px; }
  .datetime { text-align:center; padding:10px; background:#111130; color:#90caf9; font-size:0.9rem; letter-spacing:2px; }
  .table-section { padding:20px 30px; }
  .table-section h2 { color:#00e5ff; margin-bottom:15px; font-size:1rem; letter-spacing:2px; text-transform:uppercase; }
  table { width:100%; border-collapse:collapse; background:#0d0d2b; border-radius:12px; overflow:hidden; }
  thead tr { background:linear-gradient(135deg,#1a237e,#0d47a1); }
  th { padding:14px 16px; text-align:left; font-size:0.8rem; letter-spacing:1px; color:#90caf9; text-transform:uppercase; }
  tbody tr { border-bottom:1px solid #1a1a3e; }
  tbody tr:hover { background:#1a1a40; }
  td { padding:14px 16px; font-size:0.9rem; }
  .badge { display:inline-block; padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:bold; }
  .badge-csd { background:#1b5e20; color:#a5d6a7; }
  .badge-csm { background:#1a237e; color:#90caf9; }
  .present-dot { display:inline-block; width:10px; height:10px; background:#00e676; border-radius:50%; margin-right:8px; box-shadow:0 0 6px #00e676; }
  .empty-msg { text-align:center; padding:60px; color:#3d3d6b; }
  .footer { text-align:center; padding:15px; color:#3d3d6b; font-size:0.75rem; border-top:1px solid #1a1a3e; margin-top:20px; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>SMSK Smart Attendance</h1>
    <p style="color:#90caf9;font-size:0.8rem;margin-top:4px;">Face Recognition Attendance System</p>
  </div>
  <div class="live-badge">LIVE</div>
</div>
<div class="datetime">__DATA__DATETIME__</div>
<div class="stats">
  <div class="stat-card">
    <div class="number">__DATA__TOTAL__</div>
    <div class="label">Present Today</div>
  </div>
  <div class="stat-card">
    <div class="number" style="color:#69f0ae;">__DATA__CSD__</div>
    <div class="label">CSD Students</div>
  </div>
  <div class="stat-card">
    <div class="number" style="color:#ff80ab;">__DATA__CSM__</div>
    <div class="label">CSM Students</div>
  </div>
  <div class="stat-card">
    <div class="number" style="color:#ffd740;">__DATA__TIME__</div>
    <div class="label">Last Marked</div>
  </div>
</div>
<div class="table-section">
  <h2>Attendance Records</h2>
  __DATA__TABLE__
</div>
<div class="footer">
  Auto-refreshes every 5 seconds | SMSK College of Engineering | Powered by Python + DeepFace AI
</div>
</body>
</html>
"""

# ── Dashboard Server ───────────────────────────────────────
class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        today   = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().strftime("%A, %d %B %Y  |  %H:%M:%S")
        records = []

        if os.path.exists(ATTENDANCE_FILE):
            with open(ATTENDANCE_FILE, "r") as f:
                for row in csv.reader(f):
                    if len(row) >= 5 and row[3] == today:
                        records.append(row)

        total     = len(records)
        csd_count = sum(1 for r in records if r[1] == "CSD")
        csm_count = sum(1 for r in records if r[1] == "CSM")
        last_time = records[-1][4][:5] if records else "--:--"

        if records:
            rows_html = ""
            for i, r in enumerate(reversed(records), 1):
                name, dept, roll, date, time = r[0], r[1], r[2], r[3], r[4]
                badge_class = "badge-csd" if dept == "CSD" else "badge-csm"
                rows_html += f"""
                <tr>
                  <td>{i}</td>
                  <td><span class="present-dot"></span>{name}</td>
                  <td><span class="badge {badge_class}">{dept}</span></td>
                  <td>{roll}</td>
                  <td>{time}</td>
                  <td>{date}</td>
                </tr>"""
            table_html = f"""
            <table>
              <thead><tr><th>#</th><th>Name</th><th>Dept</th><th>Roll No</th><th>Time</th><th>Date</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>"""
        else:
            table_html = '<div class="empty-msg">No attendance marked yet today. Stand in front of the camera!</div>'

        html = DASHBOARD_HTML
        html = html.replace("__DATA__DATETIME__", now_str)
        html = html.replace("__DATA__TOTAL__",    str(total))
        html = html.replace("__DATA__CSD__",      str(csd_count))
        html = html.replace("__DATA__CSM__",      str(csm_count))
        html = html.replace("__DATA__TIME__",     last_time)
        html = html.replace("__DATA__TABLE__",    table_html)

        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass


def start_dashboard():
    server = HTTPServer(("localhost", DASHBOARD_PORT), DashboardHandler)
    t = threading.Thread(target=server.serve_forever)
    t.daemon = True
    t.start()
    print(f"[DASHBOARD] Running at http://localhost:{DASHBOARD_PORT}")
    webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")


# ── Helper Functions ───────────────────────────────────────
def get_student_info(key):
    key = key.lower().replace(" ", "")
    if key in STUDENT_DB:
        name, dept, roll = STUDENT_DB[key]
        return name, dept, roll
    return key.title(), "Unknown", "N/A"


def mark_attendance(name, dept, roll):
    os.makedirs("attendance_records", exist_ok=True)
    now      = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    already_marked = []
    if os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "r") as f:
            for row in csv.reader(f):
                if len(row) >= 4:
                    already_marked.append((row[0], row[3]))

    if (name, date_str) not in already_marked:
        with open(ATTENDANCE_FILE, "a", newline="") as f:
            csv.writer(f).writerow([name, dept, roll, date_str, time_str])
        print(f"[OK] Marked: {name} | {dept} | {roll} | {time_str}")
        return True, time_str
    return False, time_str


def get_known_faces():
    known = []
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith((".jpg", ".png", ".jpeg")):
            key  = os.path.splitext(filename)[0].lower().replace(" ", "")
            path = os.path.join(KNOWN_FACES_DIR, filename)
            known.append((key, path))
            name, dept, roll = get_student_info(key)
            print(f"  [OK] {name} | {dept} | {roll}")
    return known


# ── Camera Display ─────────────────────────────────────────
def draw_header(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 55), (15, 15, 80), -1)
    cv2.putText(frame, COLLEGE_NAME,
                (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    now = datetime.now().strftime("%d-%m-%Y   %H:%M:%S")
    cv2.putText(frame, now,
                (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 200, 255), 1)


def draw_info_card(frame, name, dept, roll, time_str, is_new):
    h, w   = frame.shape[:2]
    card_y = h - 165
    color  = (0, 220, 0) if is_new else (0, 165, 255)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, card_y), (w, h), (10, 10, 35), -1)
    cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)
    cv2.rectangle(frame, (0, card_y), (w, card_y + 5), color, -1)

    status = "  ATTENDANCE MARKED!" if is_new else "  ALREADY MARKED TODAY"
    cv2.putText(frame, status,
                (12, card_y + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    cv2.line(frame, (12, card_y + 42), (w - 12, card_y + 42), (60, 60, 60), 1)

    details = [("Name", name), ("Department", dept),
               ("Roll No", roll), ("Time", time_str)]
    for i, (label, value) in enumerate(details):
        y = card_y + 68 + i * 27
        txt_color = (180, 255, 180) if label == "Time" else (255, 255, 255)
        cv2.putText(frame, f"{label:<12}:  {value}",
                    (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, txt_color, 1)


def draw_scanning(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 45), (w, h), (10, 10, 10), -1)
    cv2.putText(frame, "Scanning... Look at the camera  |  Press Q to Quit",
                (10, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1)


# ── MAIN ───────────────────────────────────────────────────
def run():
    print("=" * 55)
    print(f"   {COLLEGE_NAME}")
    print("   SMART FACE ATTENDANCE SYSTEM")
    print("=" * 55)

    print("\n[INFO] Starting dashboard...")
    start_dashboard()

    print("\n[INFO] Loading student faces...")
    known_faces = get_known_faces()

    if not known_faces:
        print("[ERROR] No images found in known_faces folder!")
        return

    print(f"\n[INFO] {len(known_faces)} student(s) loaded")
    print("[INFO] Webcam starting... Press Q to quit")
    print(f"[INFO] Dashboard at http://localhost:{DASHBOARD_PORT}\n")

    speak("System is ready. Please look at the camera.")

    cap          = cv2.VideoCapture(0)
    frame_count  = 0
    display_info = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        if frame_count % 30 == 0:
            temp_path = "temp_frame.jpg"
            cv2.imwrite(temp_path, frame)

            for key, face_path in known_faces:
                try:
                    result = DeepFace.verify(
                        img1_path=temp_path,
                        img2_path=face_path,
                        enforce_detection=False,
                        silent=True
                    )
                    if result["verified"]:
                        name, dept, roll = get_student_info(key)
                        is_new, time_str = mark_attendance(name, dept, roll)
                        display_info     = [name, dept, roll, time_str, is_new, 90]

                        if is_new:
                            speak(f"{name}, your attendance has been marked successfully.")
                        else:
                            speak(f"{name}, your attendance is already marked today.")
                        break
                except Exception:
                    pass

            if os.path.exists(temp_path):
                os.remove(temp_path)

        draw_header(frame)

        if display_info and display_info[5] > 0:
            name, dept, roll, time_str, is_new, countdown = display_info
            draw_info_card(frame, name, dept, roll, time_str, is_new)
            display_info[5] -= 1
        else:
            draw_scanning(frame)

        cv2.imshow("SMSK - Smart Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            speak("Attendance session ended.")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Session ended.")
    print(f"[INFO] Records saved to: {ATTENDANCE_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    run()
 