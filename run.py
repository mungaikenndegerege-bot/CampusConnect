"""
run.py — Local development server.
Usage: python run.py
"""
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from seed import seed_super_admin

app = create_app()

# Create tables and seed super admin on startup
seed_super_admin(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
