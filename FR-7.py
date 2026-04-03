import datetime

def generate_recommendations(health_data):
    """
    health_data expects keys:
      - steps (int)
      - hydration_liters (float)
      - sleep_hours (float)
      - stress_level (0-10 optional)
      - resting_heart_rate (int optional)
    Returns a structure with category recommendations and generation timestamp.
    """
    now = datetime.datetime.utcnow()

    steps = health_data.get("steps", 0)
    hydration = health_data.get("hydration_liters", 0.0)
    sleep = health_data.get("sleep_hours", 0.0)
    stress = health_data.get("stress_level", None)
    rhr = health_data.get("resting_heart_rate", None)

    recommendations = {}

    # Hydration category
    if hydration < 1.5:
        recommendations["hydration"] = (
            f"Your reported hydration is low ({hydration:.1f} L). "
            "Aim to drink 0.5-1.0 L in the next 2 hours, and track fluids "
            "to reach at least 2.0 L today."
        )
    elif hydration < 2.5:
        recommendations["hydration"] = (
            f"Good progress ({hydration:.1f} L). Keep sipping water consistently "
            "throughout the day to hit 2.5 L."
        )
    else:
        recommendations["hydration"] = (
            f"Excellent hydration ({hydration:.1f} L). Maintain the habit."
        )

    # Activity category
    if steps < 5000:
        recommendations["activity"] = (
            f"Low step count ({steps} steps). "
            "Do a 20-30 minute brisk walk or light cardio now "
            "to approach 7,500+ steps."
        )
    elif steps < 10000:
        recommendations["activity"] = (
            f"Moderate steps ({steps}). "
            "Add one extra walking session or stairs to hit 10,000 steps."
        )
    else:
        recommendations["activity"] = (
            f"Great activity level ({steps} steps). Keep this up "
            "and consider strength/stretching after your walk."
        )

    # Sleep category
    if sleep <= 0:
        recommendations["sleep"] = "No sleep record detected. Log your last sleep duration."
    elif sleep < 7:
        recommendations["sleep"] = (
            f"Sleep is low ({sleep:.1f} hrs). "
            "Target 7-9 hours tonight, wind down 1 hour before bed."
        )
    elif sleep <= 9:
        recommendations["sleep"] = (
            f"Sleep good ({sleep:.1f} hrs). Keep consistent bedtime/wake schedule."
        )
    else:
        recommendations["sleep"] = (
            f"High sleep duration ({sleep:.1f} hrs). "
            "Evaluate sleep quality and avoid excessive daytime napping."
        )

    # General wellness category
    wellness_items = []
    if stress is not None:
        if stress >= 7:
            wellness_items.append(
                f"Stress level high ({stress}/10). Try breathing exercises "
                "or a short mindfulness session."
            )
        elif stress >= 4:
            wellness_items.append(
                f"Moderate stress ({stress}/10). Protect breaks and hydration."
            )
        else:
            wellness_items.append("Low reported stress. Keep the good habits.")

    if rhr is not None:
        if rhr > 90:
            wellness_items.append(
                f"Resting heart rate is elevated ({rhr} bpm). "
                "Ensure recovery and consult provider if persistent."
            )
        elif rhr < 50:
            wellness_items.append(
                f"Low resting heart rate ({rhr} bpm). If you are a trained athlete, this is great."
            )
        else:
            wellness_items.append(
                f"Resting heart rate is in a normal range ({rhr} bpm)."
            )

    if not wellness_items:
        wellness_items.append("General wellness: keep a balanced diet, hydration, and movement.")

    recommendations["wellness"] = " ".join(wellness_items)

    latency_ms = int((datetime.datetime.utcnow() - now).total_seconds() * 1000)

    return {
        "generated_at": now.isoformat() + "Z",
        "latency_ms": latency_ms,
        "source_data": health_data,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    sample_data = {
        "steps": 4200,
        "hydration_liters": 1.2,
        "sleep_hours": 6.2,
        "stress_level": 6,
        "resting_heart_rate": 88,
    }

    result = generate_recommendations(sample_data)
    print(result)