import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import initialize_database


if __name__ == "__main__":
    result = initialize_database()
    print(json.dumps(result, ensure_ascii=False, indent=2))
