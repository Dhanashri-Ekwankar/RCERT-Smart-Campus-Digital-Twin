"""Flask compatibility entry point; implementation lives in application.py."""
from application import app, CAMPUS, CAMPUS_ZONES
from database import initialize_database

if __name__ == "__main__":
    initialize_database()
    print("RCERT Smart Campus Digital Twin")
    print("Dashboard: http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
