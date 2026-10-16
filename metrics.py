# Metrics for comparing FIFO and greedy on the same input data

import math

from Algo import deadline_of

# "Urgent" = the earliest-expiring 25% of donations (by deadline = ready_time + expire_time).
# Donations tied with the last one in that group count as urgent too.
URGENT_FRACTION = 0.25


def urgent_donation_ids(donations):
    """Returns the set of donation IDs that count as urgent."""
    donation_list = list(donations.values()) if isinstance(donations, dict) else list(donations)
    if not donation_list:
        return set()
    by_deadline = sorted(donation_list, key=deadline_of)
    count = math.ceil(len(donation_list) * URGENT_FRACTION)
    cutoff = deadline_of(by_deadline[count - 1])
    return {d["donation_id"] for d in donation_list if deadline_of(d) <= cutoff}


def _percent(part, whole):
    return 100.0 * part / whole if whole else 0.0


def compute_metrics(results, donations, recipients, volunteers):
    """Calculates the required metrics for one strategy's results.

    results is the list of Assignments returned by fifo_schedule or greedy_schedule.
    Percentages are 0-100. Utilization compares the assigned quantity with the total
    starting capacity of all recipients / all volunteer vehicles.

    Time: O(D log D + R + V), the D log D is from finding the urgent donations.
    """
    donation_list = list(donations.values()) if isinstance(donations, dict) else list(donations)
    recipient_list = list(recipients.values()) if isinstance(recipients, dict) else list(recipients)
    volunteer_list = list(volunteers.values()) if isinstance(volunteers, dict) else list(volunteers)

    quantity = {d["donation_id"]: d["quantity"] for d in donation_list}
    assigned = {a.donation_id for a in results if a.status == "assigned"}
    urgent = urgent_donation_ids(donation_list)

    rescued = sum(quantity[d_id] for d_id in assigned)
    total_quantity = sum(quantity.values())
    recipient_capacity = sum(r["capacity"] for r in recipient_list)
    vehicle_capacity = sum(v["vehicle_capacity"] for v in volunteer_list)

    return {
        "donations_received": len(donation_list),
        "donations_assigned": len(assigned),
        "donations_unassigned": len(donation_list) - len(assigned),
        "quantity_rescued": rescued,
        "quantity_at_risk": total_quantity - rescued,
        "urgent_donations": len(urgent),
        "urgent_assigned": len(urgent & assigned),
        "urgent_rescue_rate": _percent(len(urgent & assigned), len(urgent)),
        "recipient_capacity_utilization": _percent(rescued, recipient_capacity),
        "volunteer_capacity_utilization": _percent(rescued, vehicle_capacity),
    }


def format_metrics(metrics):
    """Returns the metrics as readable lines for the command-line output."""
    m = metrics
    return "\n".join([
        f"Donations received:             {m['donations_received']}",
        f"Donations assigned:             {m['donations_assigned']}",
        f"Donations unassigned:           {m['donations_unassigned']}",
        f"Food quantity rescued:          {m['quantity_rescued']} units",
        f"Food quantity at risk:          {m['quantity_at_risk']} units",
        f"Urgent rescue rate:             {m['urgent_rescue_rate']:.1f}% "
        f"({m['urgent_assigned']} of {m['urgent_donations']} earliest-expiring donations)",
        f"Recipient capacity utilization: {m['recipient_capacity_utilization']:.1f}%",
        f"Volunteer capacity utilization: {m['volunteer_capacity_utilization']:.1f}%",
    ])


# FIFO vs greedy comparison

_COMPARED = [
    ("donations_assigned", "Donations assigned", "{:d}"),
    ("donations_unassigned", "Donations unassigned", "{:d}"),
    ("quantity_rescued", "Food quantity rescued", "{:d}"),
    ("quantity_at_risk", "Food quantity at risk", "{:d}"),
    ("urgent_rescue_rate", "Urgent rescue rate (%)", "{:.1f}"),
    ("recipient_capacity_utilization", "Recipient utilization (%)", "{:.1f}"),
    ("volunteer_capacity_utilization", "Volunteer utilization (%)", "{:.1f}"),
]


def compare_metrics(fifo_metrics, greedy_metrics):
    """Returns greedy minus FIFO for each compared metric (positive = greedy is higher)."""
    return {key: greedy_metrics[key] - fifo_metrics[key] for key, _, _ in _COMPARED}


def _because(reason):
    # "Donation D1 could not be assigned because X." -> "X."
    return reason.split(" because ", 1)[1] if " because " in reason else reason


def _change(amount, unit):
    # 2 -> "2 more donations", -1 -> "1 fewer donations", 0 -> "the same number of donations"
    if amount == 0:
        return f"the same number of {unit}"
    return f"{abs(amount)} {'more' if amount > 0 else 'fewer'} {unit}"


def explain_comparison(fifo_results, greedy_results, fifo_metrics, greedy_metrics):
    """Explains what changed between the two strategies and why, as a list of sentences.

    Both strategies use the same matching step, so any difference comes only from the
    order donations were handled in. For each donation whose outcome changed, the
    explanation uses the reason the losing strategy gave for not assigning it.
    """
    fifo = {a.donation_id: a for a in fifo_results}
    greedy = {a.donation_id: a for a in greedy_results}
    diff = compare_metrics(fifo_metrics, greedy_metrics)
    lines = []

    gained = [d for d in fifo if fifo[d].status != "assigned" and greedy[d].status == "assigned"]
    lost = [d for d in fifo if fifo[d].status == "assigned" and greedy[d].status != "assigned"]
    moved = [d for d in fifo if fifo[d].status == greedy[d].status == "assigned"
             and (fifo[d].recipient_id, fifo[d].volunteer_id)
             != (greedy[d].recipient_id, greedy[d].volunteer_id)]

    if not gained and not lost:
        lines.append("Both strategies assigned the same donations, so switching from arrival "
                     "order to urgency order did not change any outcome on this data.")
    else:
        lines.append(
            f"Compared with FIFO, greedy assigned {_change(diff['donations_assigned'], 'donations')}, "
            f"rescued {_change(diff['quantity_rescued'], 'units')} of food, and its urgent rescue "
            f"rate went from {fifo_metrics['urgent_rescue_rate']:.1f}% to "
            f"{greedy_metrics['urgent_rescue_rate']:.1f}%. Both strategies use the same matching "
            f"rules, so every difference comes from the order donations were handled in.")
        for d in gained:
            lines.append(f"{d} was assigned only under greedy. Greedy handled it before "
                         f"donations that expire later; under FIFO it was handled in arrival "
                         f"order and could not be assigned because {_because(fifo[d].reason)}")
        for d in lost:
            lines.append(f"{d} was assigned only under FIFO, where it arrived early enough to "
                         f"claim capacity. Under greedy it could not be assigned because "
                         f"{_because(greedy[d].reason)}")

    for d in moved:
        lines.append(f"{d} was assigned under both, but to {greedy[d].recipient_id} / "
                     f"{greedy[d].volunteer_id} under greedy instead of {fifo[d].recipient_id} / "
                     f"{fifo[d].volunteer_id} under FIFO, because earlier donations had used "
                     f"different capacity.")
    return lines


def format_comparison(fifo_metrics, greedy_metrics):
    """Returns a FIFO | Greedy | Difference table as text."""
    diff = compare_metrics(fifo_metrics, greedy_metrics)
    rows = [f"{'Metric':<28}{'FIFO':>10}{'Greedy':>10}{'Difference':>12}"]
    for key, label, fmt in _COMPARED:
        change = ("+" if diff[key] > 0 else "") + fmt.format(diff[key])
        rows.append(f"{label:<28}{fmt.format(fifo_metrics[key]):>10}"
                    f"{fmt.format(greedy_metrics[key]):>10}{change:>12}")
    return "\n".join(rows)
