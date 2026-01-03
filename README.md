# FRC Cycles Calculator

Simple Streamlit app to calculate possible cycle times and estimated scores for FRC.

Run locally:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Usage:
- Upload a CSV with rows: Action name, Duration (sec), Qualification Pts, Playoffs Pts, Probability (in decimal, e.g. 0.9)
- Define a global time (e.g., 135)
- Use the "Add new cycle" expander to name a cycle, pick actions (indexed on the actions table) and provide an ordering as comma-separated indices.
- Add multiple cycles; view the summary table and download an Excel file.
"# CycleCalculator" 
