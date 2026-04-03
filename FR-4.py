import json
import os

class HealthProfile:
    def __init__(self, user_id):
        self.user_id = user_id
        self.data_file = f"profile_{user_id}.json"
        self.profile = self.load_profile()

    def load_profile(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {"age": None, "weight": None, "height": None, "medical_conditions": []}

    def save_profile(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.profile, f)

    def update_field(self, field, value):
        if field in self.profile:
            self.profile[field] = value
            self.save_profile()
        else:
            raise ValueError("Invalid field")

    def get_profile(self):
        return self.profile

    def get_recommendation_data(self):
        # Prepare data for AI recommendations (FR-7)
        return {
            "age": self.profile["age"],
            "bmi": self.calculate_bmi(),
            "conditions": self.profile["medical_conditions"]
        }

    def calculate_bmi(self):
        if self.profile["weight"] and self.profile["height"]:
            return self.profile["weight"] / (self.profile["height"] ** 2)
        return None