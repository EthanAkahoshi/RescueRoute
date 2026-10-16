import os

from RescueRouter_Data import load_all_data
from Algo import fifo_schedule, greedy_schedule
from metrics import compute_metrics, format_metrics

# load_all_data uses paths like ./input_data/..., so run from this file's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

donations, recipients, volunteers = load_all_data()


def run(name, schedule):
    print(f"=== {name} ===")
    results = schedule(donations, recipients, volunteers)

    for a in results:
        print(f"[{a.status}] {a.reason}")

    metrics = compute_metrics(results, donations, recipients, volunteers)
    print()
    print(format_metrics(metrics))
    print()
    return metrics


fifo_metrics = run("FIFO", fifo_schedule)
greedy_metrics = run("Greedy (urgency-first)", greedy_schedule)
