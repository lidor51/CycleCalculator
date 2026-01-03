import math
import pandas as pd

def compute_cycle_summary(df: pd.DataFrame, name: str, action_indices: list, global_time: float) -> dict:
    actions = df.loc[action_indices]
    cycle_time = float(actions["duration"].sum())
    qual_pts = float(actions["qual_pts"].sum())
    playoff_pts = float(actions["playoff_pts"].sum())
    prob = float(actions["prob"].prod()) if len(actions) > 0 else 0.0
    total_cycles = int(math.floor(global_time / cycle_time)) if cycle_time > 0 else 0
    total_qualification_score = qual_pts * total_cycles
    estimated_qualification_score = total_qualification_score * prob
    total_playoffs_score = playoff_pts * total_cycles
    estimated_playoffs_score = total_playoffs_score * prob
    pts_per_sec = (playoff_pts / cycle_time) if cycle_time > 0 else 0.0
    estimated_pts_per_sec = pts_per_sec * prob
    action_names = actions["name"].tolist()

    return {
        "Cycle name": name,
        "Cycle actions": " → \r\n".join(action_names),
        "Cycle time": cycle_time,
        "Qualification Pts": qual_pts,
        "Playoff Pts": playoff_pts,
        "Probability": prob,
        "Total cycles": total_cycles,
        "Total Qualification Score": total_qualification_score,
        "Estimated Qualification Score": estimated_qualification_score,
        "Total Playoffs Score": total_playoffs_score,
        "Estimated Playoffs Score": estimated_playoffs_score,
        "Pts-per-sec": pts_per_sec,
        "Estimated Pts-per-sec": estimated_pts_per_sec,
    }
