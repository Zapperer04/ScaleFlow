import os
task_dir = r"C:\Users\Kaustav\.gemini\antigravity-ide\brain\557aa795-8cfc-41c2-ad19-5870e708b5be\.system_generated\tasks"
if os.path.exists(task_dir):
    print("Files in tasks dir:")
    for f in os.listdir(task_dir):
        print(f" - {f}")
else:
    print("Tasks dir does not exist")
