import os

from RescueRouter_Data import load_all_data
from Algo import fifo_schedule

# load_all_data uses paths like ./input_data/..., so run from this file's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

donations, recipients, volunteers = load_all_data()

print("=== FIFO ===")
results = fifo_schedule(donations, recipients, volunteers)

for a in results:
    print(f"[{a.status}] {a.reason}")

assigned = [a for a in results if a.status == "assigned"]
total_food = sum(donations[a.donation_id]["quantity"] for a in assigned)

print()
print(f"Assigned: {len(assigned)} / {len(results)} donations")
print(f"Food delivered: {total_food} units")
