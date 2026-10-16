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
