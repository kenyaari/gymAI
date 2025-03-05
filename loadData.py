import sqlite3
import pandas as pd

DB_NAME = "workout_data.db"
CSV_FILE = "megaGymDataset.csv"

MUSCLE_MAPPING = {
    "chest": ["chest", "bench press", "chest fly", "pec deck", "push-up"],
    "triceps": ["tricep", "triceps", "triceps dip", "triceps extension", "skull crusher"],
    "biceps": ["bicep", "biceps", "bicep curl", "hammer curl", "chin-up"],
    "forearms": ["forearm", "forearms"],
    "neck": ["neck"],
    "shoulders": ["shoulder", "shoulders", "shoulder press", "traps"],
    "deltoids": ["deltoid", "deltoids", "lateral raise"],
    "back": ["lat", "pull-up", "deadlift", "lat pulldown", "row", "lower back", "middle back"],
    "quadriceps": ["quadricep", "quadriceps", "squat", "leg press", "lunges"],
    "hamstrings": ["hamstring", "hamstrings", "deadlift", "romanian deadlift", "leg curl"],
    "glutes": ["glute", "glutes", "hip thrust", "glute bridge", "bulgarian split squat"],
    "calves": ["calf", "calves", "calf raise", "seated calf raise"],
    "core": ["abs", "core", "ab", "plank", "sit-up", "ab rollout", "crunch"]
}

DEFAULT_REPS_SETS = {
    "Strength": {"reps": 4, "sets": 5},
    "Plyometrics": {"reps": 8, "sets": 4},
    "Cardio": {"reps": 20, "sets": 1},
    "Stretching": {"reps": 30, "sets": 3},
    "Powerlifting": {"reps": 3, "sets": 5},
    "Strongman": {"reps": 6, "sets": 4},
    "Olympic Weightlifting": {"reps": 2, "sets": 6}
}

def reset_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS workouts")
    cur.execute("DROP TABLE IF EXISTS muscles")
    cur.execute("DROP TABLE IF EXISTS workout_muscle_map")
    cur.execute("DROP TABLE IF EXISTS workouts_old")
    conn.commit()
    conn.close()
    create_db()

def create_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
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
    cur.execute("""CREATE TABLE IF NOT EXISTS muscles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        muscle_name TEXT UNIQUE
                      )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS workout_muscle_map (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workout_id INTEGER,
                        muscle_id INTEGER,
                        FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
                        FOREIGN KEY (muscle_id) REFERENCES muscles(id) ON DELETE CASCADE
                      )""")
    conn.commit()
    conn.close()

def get_default_reps_sets(physique_goal):
    return DEFAULT_REPS_SETS.get(physique_goal, {"reps": 6, "sets": 3})

def map_muscle_group(title, description):
    title_lower = title.lower() if isinstance(title, str) else ""
    description_lower = description.lower() if isinstance(description, str) else ""
    matched_muscles = [
        muscle for muscle, keywords in MUSCLE_MAPPING.items()
        if any(keyword in title_lower or keyword in description_lower for keyword in keywords)
    ]
    return ", ".join(matched_muscles) if matched_muscles else "Other"

def csv_to_sqlite(csv_file):
    df = pd.read_csv(csv_file)
    #df.drop_duplicates(inplace=True, keep='first')
    df.drop(columns=["Rating", "RatingDesc"], errors="ignore", inplace=True)
    df = df.rename(columns={
        "Title": "title",
        "Desc": "workout_description",
        "Type": "physique_goal",
        "BodyPart": "target_muscle",
        "Level": "experience_level"
    })
    df = df[["title", "workout_description", "physique_goal", "target_muscle", "experience_level"]]
    df["workout_description"].fillna("No description available.", inplace=True)
    df["experience_level"].fillna("Beginner", inplace=True)
    df.dropna(subset=["title", "physique_goal", "target_muscle"], inplace=True)
    print(f"Total rows after missing value processing: {len(df)}")
    df["reps"] = df["physique_goal"].apply(lambda goal: get_default_reps_sets(goal)["reps"])
    df["sets"] = df["physique_goal"].apply(lambda goal: get_default_reps_sets(goal)["sets"])
    df["target_muscle"] = df.apply(lambda row: map_muscle_group(row["title"], row["workout_description"]), axis=1)

    df.to_csv("updated_megaGymDataset.csv", index=False)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    df.to_sql("workouts", conn, if_exists="append", index=False)

    unique_muscles = set(df["target_muscle"].dropna().unique())
    for muscle in unique_muscles:
        cur.execute("INSERT OR IGNORE INTO muscles (muscle_name) VALUES (?)", (muscle,))
    
    df.to_sql("workouts", conn, if_exists="replace", index=False, chunksize=500)

    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO workouts (title, workout_description, physique_goal, experience_level, reps, sets)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (row["title"], row["workout_description"], row["physique_goal"], row["experience_level"], row["reps"], row["sets"]))
        workout_id = cur.lastrowid
        muscles = [muscle.strip() for muscle in row["target_muscle"].split(",")]
        for muscle in muscles:
            cur.execute("INSERT OR IGNORE INTO muscles (muscle_name) VALUES (?)", (muscle,))
            cur.execute("SELECT id FROM muscles WHERE muscle_name = ?", (muscle,))
            muscle_id = cur.fetchone()[0]
            cur.execute("INSERT INTO workout_muscle_map (workout_id, muscle_id) VALUES (?, ?)", (workout_id, muscle_id))
    conn.commit()
    conn.close()

def fetch_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM workouts", conn)
    print(f"\nTotal rows retrieved from workouts database: {len(df)}")
    df = pd.read_sql_query("SELECT * FROM muscles", conn)
    print(f"\nTotal rows retrieved from muscles database: {len(df)}")
    df = pd.read_sql_query("SELECT * FROM workout_muscle_map", conn)
    print(f"\nTotal rows retrieved from workout_muscle_map database: {len(df)}")
    conn.close()
    print("Sample Data:\n", df.head(5))
    return df

if __name__ == "__main__":
    reset_db()
    csv_to_sqlite(CSV_FILE)
    data = fetch_data()