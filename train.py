import torch.nn as nn
import torch.optim as optim
import sqlite3
import numpy as np
import pandas as pd
import torch
import re
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer

USER_MUSCLE_MAPPING = {
    "arms": ["biceps", "triceps", "forearms"],
    "legs": ["quadriceps", "hamstrings", "glutes", "calves"],
    "chest": ["chest"],
    "back": ["lats", "traps", "lower back"],
    "shoulders": ["shoulders", "deltoids"],
    "core": ["core"]
}

def train():
    DB_NAME = "workout_data.db"
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS workouts_old;")
    cur.execute("ALTER TABLE workouts RENAME TO workouts_old;")
    cur.execute("""CREATE TABLE workouts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT,
                   workout_description TEXT,
                   physique_goal TEXT,
                   target_muscle TEXT,
                   experience_level TEXT,
                   reps INTEGER DEFAULT 10,
                   sets INTEGER DEFAULT 3,
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
               );""")
    cur.execute("""INSERT INTO workouts (title, workout_description, physique_goal, target_muscle, experience_level, reps, sets)
                   SELECT title, workout_description, physique_goal, target_muscle, experience_level, reps, sets FROM workouts_old;""")
    cur.execute("DROP TABLE IF EXISTS workouts_old;")

    query = """
        SELECT w.id, w.physique_goal, GROUP_CONCAT(m.muscle_name) AS target_muscles
        FROM workouts w
        JOIN workout_muscle_map wm ON w.id = wm.workout_id
        JOIN muscles m ON wm.muscle_id = m.id
        GROUP BY w.id
    """
    df = pd.read_sql_query(query, conn)
    conn.commit()
    conn.close()

    goal_encoder = LabelEncoder()
    df["goal_encoded"] = goal_encoder.fit_transform(df["physique_goal"])

    df["target_muscles"] = df["target_muscles"].apply(lambda x: x.split(","))
    mlb = MultiLabelBinarizer()
    muscle_vectors = mlb.fit_transform(df["target_muscles"])

    X = torch.tensor(np.hstack((muscle_vectors, df["goal_encoded"].values.reshape(-1, 1))), dtype=torch.float32)
    y = torch.arange(X.shape[0])

    def fetch_muscle_vectors():
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("SELECT id, muscle_name FROM muscles;")
        muscles = {muscle[1]: muscle[0] for muscle in cur.fetchall()}

        cur.execute("""
            SELECT w.id, m.muscle_name
            FROM workouts w
            JOIN workout_muscle_map wm ON w.id = wm.workout_id
            JOIN muscles m ON wm.muscle_id = m.id;
        """)
        data = cur.fetchall()
        conn.commit()
        conn.close()

        exercise_to_vector = {}
        all_muscle_names = list(muscles.keys())
        for exercise_id, muscle in data:
            if exercise_id not in exercise_to_vector:
                exercise_to_vector[exercise_id] = torch.zeros(len(all_muscle_names))
            try:
                muscle_index = all_muscle_names.index(muscle)
                exercise_to_vector[exercise_id][muscle_index] = 1 
            except ValueError:
                print(f"Warning: Muscle '{muscle}' not found in all_muscle_names")
        return exercise_to_vector, muscles

    class WorkoutRecommendationModel(nn.Module):
        def __init__(self, input_size, hidden_size, output_size):
            super(WorkoutRecommendationModel, self).__init__()
            self.fc1 = nn.Linear(input_size, hidden_size)
            self.relu = nn.ReLU()
            self.fc2 = nn.Linear(hidden_size, output_size)

        def forward(self, x):
            x = self.fc1(x)
            x = self.relu(x)
            x = self.fc2(x)
            return x

    exercise_vectors, muscle_dict = fetch_muscle_vectors()
    input_size = len(muscle_dict)

    input_size = X.shape[1]
    hidden_size = 32
    output_size = len(df)

    model = WorkoutRecommendationModel(input_size, hidden_size, output_size)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    epochs = 1000
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()

        if epoch % 100 == 0:
            print(f"Epoch [{epoch}/{epochs}], Loss: {loss.item():.4f}")
    print("Training Complete!")

if __name__ == "__main__":
    train()