"""Run the self-contained skill helper from a source checkout."""
import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "skills" / "expert-workgroup" / "scripts" / "expert_group.py"), run_name="__main__")
