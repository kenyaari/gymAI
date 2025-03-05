import sqlite3
import re
import random

DB_NAME = 'workout_data.db'

USER_MUSCLE_MAPPING = {
    "arms": ["biceps", "triceps", "forearms"],
    "legs": ["quadriceps", "hamstrings", "glutes", "calves"],
    "chest": ["chest"],
    "back": ["back"],
    "shoulders": ["shoulders", "deltoids"],
    "core": ["core"],
    "abs": ["core"],
    "biceps": ["biceps"],
    "triceps": ["triceps"],
    "forearms": ["forearms"],
    "quadriceps": ["quadriceps"],
    "hamstrings": ["hamstrings"],
    "glutes": ["glutes"],
    "calves": ["calves"],
    "lats": ["lats"],
    "traps": ["traps"],
    "deltoids": ["deltoids"]
}

muscle_exercise_queue = {}

def get_next_exercises(target_muscle, limit=2):
    """Cycles through all available exercises before repeating."""
    global muscle_exercise_queue

    if target_muscle not in muscle_exercise_queue or not muscle_exercise_queue[target_muscle]:
        # Fetch and shuffle exercises when queue is empty
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        query = """
            SELECT w.title, w.workout_description, w.reps, w.sets
            FROM workouts w
            JOIN workout_muscle_map wm ON w.id = wm.workout_id
            JOIN muscles m ON wm.muscle_id = m.id
            WHERE m.muscle_name = ?;
        """
        cur.execute(query, (target_muscle,))
        all_workouts = cur.fetchall()
        conn.commit()
        conn.close()
        random.shuffle(all_workouts)
        muscle_exercise_queue[target_muscle] = all_workouts

    recommended = muscle_exercise_queue[target_muscle][:limit]
    muscle_exercise_queue[target_muscle] = muscle_exercise_queue[target_muscle][limit:]  # Rotate queue

    return recommended

def parse_user_input(user_input):
    user_input = user_input.lower()
    matched_muscles = []

    for key, muscles in USER_MUSCLE_MAPPING.items():
       if re.search(rf"\b{key}\b", user_input):
            matched_muscles.extend(muscles)

    return matched_muscles

def recommend_exercises(user_request):
    body_parts = parse_user_input(user_request)
    if not body_parts:
        print("No relevant muscles found. Please refine your request.")
        return
    if len(body_parts) > 1:
        print("Which particular muscle would you like to work on: "+", ".join(body_parts)+"?")
        response = input()
        while response not in body_parts:
            print("Enter a muscle among the list above.")
            response = input()
        body_parts = response
    else:
        body_parts = body_parts[0]
    workouts = get_next_exercises(body_parts)
    if workouts:
        print("Recommended Exercises:")
        for i, w in enumerate(workouts):
            print(str(i+1)+". "+w[0])
            print("Description: "+w[1])
            print("Reps: "+str(w[2])+" Sets: "+str(w[3])+"\n")
    else:
        print("No exercises were found. Please refine your request.")

if __name__ == "__main__":
    print("Enter what muscles you would like to work on. Type 'Done' to finish.")
    user_request = input()
    while user_request != 'Done':
        recommend_exercises(user_request)
        print("Please type what muscles you would like to work on. Type 'Done' to finish.")
        user_request = input()
