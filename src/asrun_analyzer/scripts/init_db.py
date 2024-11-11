import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.asrun_analyzer.database import init_db
from src.asrun_analyzer.models import Base

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")