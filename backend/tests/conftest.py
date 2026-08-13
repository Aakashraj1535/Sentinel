import sys
from pathlib import Path

# So `import app.xxx` works when pytest is run from the backend/ folder
# or from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
