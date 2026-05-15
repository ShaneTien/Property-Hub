---
name: feedback-python-runner
description: Use python to run scripts in this project — full path if needed
metadata:
  type: feedback
---

Use `python` to run Python scripts in this project. The interpreter is installed at:
`C:\Users\Shane Tien\AppData\Local\Python\pythoncore-3.14-64\python.exe`

All packages (requests, pandas, pyproj, pydeck, streamlit, altair, etc.) are installed in that environment.

**Why:** uv is available but python is the preferred runner. Do not use `uv run` unless explicitly asked.

**How to apply:** Run scripts with `python scripts/foo.py` (or the full path if `python` isn't resolving).
