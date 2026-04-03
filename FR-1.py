import time
import random

class ActivityTracker:
    def __init__(self):
        self.step_count = 0
        self.active_minutes = 0
        self.calories_burned = 0
        self.last_update = time.time()

    def update_metrics(self):
        # Simulate data update (in a real app, this would integrate with sensors or APIs)
        current_time = time.time()
        elapsed = current_time - self.last_update
        if elapsed >= 300:  # Update every 5 minutes
            self.step_count += random.randint(100, 500)
            self.active_minutes += random.randint(5, 20)
            self.calories_burned += random.randint(50, 200)
            self.last_update = current_time

    def display_dashboard(self):
        self.update_metrics()
        print("Daily Activity Dashboard:")
        print(f"Step Count: {self.step_count}")
        print(f"Active Minutes: {self.active_minutes}")
        print(f"Estimated Calories Burned: {self.calories_burned}")
        print("Data refreshes every 5 minutes during active use.")

    def get_historical_data(self):
        # Placeholder for historical data storage (e.g., database integration)
        return {"date": "2023-10-01", "steps": self.step_count, "active_min": self.active_minutes, "calories": self.calories_burned}

# Example usage
tracker = ActivityTracker()
tracker.display_dashboard()
# In a real application, this would be integrated into a web or mobile dashboard with real-time updates.