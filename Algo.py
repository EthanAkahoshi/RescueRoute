#donations (Time that the food is good)
#recipents (Can only take certain food and closes at certain times)
#volunteers (Works certain hours and can only do certain trips)

#Two ways to handle this:
#FIFO Handle donations as they arrive
#greedy urgency handle dontations in a way that donations that expeires first gets delievered

def deadline_of(donation):
    return donation["ready_time"] + donation["expire_time"]

def check_time(donation, recipient, volunteer):
    deadline = deadline_of(donation)
    vol_start, vol_end = volunteer["availability"]
    pickup_time = max(donation["ready_time"], vol_start)

    if pickup_time > deadline:
        return False, f"it expires at {deadline}, before the pick up time of {pickup_time}"
    if pickup_time > vol_end:
        return False, f"The voulteer shift ends at {vol_end}"
    if pickup_time > recipient["closing_time"]:
        return False, f"{recipient['organization_name']}, closes at {recipient['closing_time']} "
    return True, pickup_time

# FIFO baseline

import heapq
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class Assignment:
    donation_id: str
    recipient_id: Optional[str]     # None when unassigned
    volunteer_id: Optional[str]     # None when unassigned
    scheduled_time: Optional[int]   # pickup time in minutes from midnight, None when unassigned
    reason: str                     # human-readable explanation of the decision
    status: str                     # "assigned" or "unassigned"


def _fmt_time(minutes):
    # 480 -> "8:00 AM"; deadlines can run past midnight (ready_time + expire_time > 1440)
    day, minutes = divmod(minutes, 1440)
    hours, mins = divmod(minutes, 60)
    suffix = "AM" if hours < 12 else "PM"
    text = f"{hours % 12 or 12}:{mins:02d} {suffix}"
    return text + " the next day" if day else text


def fifo_schedule(donations, recipients, volunteers):
    """FIFO = first come, first served.

    We go through the donations in the order they're ready (earliest first).

    For each donation:
    - pick the first recipient that takes that food, has room, and is still open
    - pick the first volunteer who has room in their car, isn't at their pickup
      limit, and can get there before the food goes bad

    It doesn't plan ahead, so sometimes an early donation takes a spot a later one
    needed more. Greedy is supposed to fix that.

    It doesn't change the original data, so you can run greedy on it after.

    Returns a list with one Assignment for every donation.

    Time: O(D log D + D * (R + V))
    D = donations, R = recipients, V = volunteers.
    The D log D is from sorting, and the rest is checking the lists for each donation.
    """
    donation_list = list(donations.values()) if isinstance(donations, dict) else list(donations)
    recipient_list = list(recipients.values()) if isinstance(recipients, dict) else list(recipients)
    volunteer_list = list(volunteers.values()) if isinstance(volunteers, dict) else list(volunteers)

    # Local copies of everything FIFO changes, so the input data stays untouched
    rec_capacity = {r["recipient_id"]: r["capacity"] for r in recipient_list}
    rec_accepts = {r["recipient_id"]: set(r["accepted_food_types"]) for r in recipient_list}
    vol_capacity = {v["volunteer_id"]: v["vehicle_capacity"] for v in volunteer_list}
    vol_pickups = {v["volunteer_id"]: v["pickup_counter"] for v in volunteer_list}

    queue = deque(sorted(donation_list, key=lambda d: d["ready_time"]))
    results = []
    while queue:
        donation = queue.popleft()
        results.append(_assign_one(donation, recipient_list, volunteer_list,
                                   rec_capacity, rec_accepts, vol_capacity, vol_pickups))
    return results


# Greedy urgency-first

def _greedy_key(donation, arrival):
    # Smaller key = handled sooner:
    #   1. earliest expiry deadline (ready_time + expire_time)
    #   2. larger quantity (rescues more food when deadlines tie)
    #   3. earlier ready time
    #   4. arrival position (makes the order fully deterministic)
    return (deadline_of(donation), -donation["quantity"], donation["ready_time"], arrival)


def _priority_reason(first, second):
    # Explains which part of the greedy rule put `first` ahead of `second`
    f_id, s_id = first["donation_id"], second["donation_id"]
    if deadline_of(first) != deadline_of(second):
        return (f"{f_id} expires at {_fmt_time(deadline_of(first))}, before {s_id} "
                f"expires at {_fmt_time(deadline_of(second))}")
    if first["quantity"] != second["quantity"]:
        return (f"both expire at {_fmt_time(deadline_of(first))} and {f_id} is larger "
                f"({first['quantity']} vs {second['quantity']} units)")
    return (f"both expire at {_fmt_time(deadline_of(first))} with the same quantity "
            f"and {f_id} arrived first")


def greedy_schedule(donations, recipients, volunteers):
    """Greedy urgency-first.

    Rule: handle the donation that expires soonest first (deadline = ready_time +
    expire_time). If two expire at the same time, handle the larger quantity first.
    If still tied, the one that was ready earlier goes first.

    Each donation is then matched exactly like FIFO (first recipient / volunteer that
    works), so the only difference between the two strategies is the order.

    What it optimizes locally: the food closest to going bad gets first pick of the
    recipient capacity and volunteers, instead of losing it to food that could wait.

    Where it can fail: it doesn't look ahead. An urgent donation can use up a
    recipient that a later donation needed more (e.g. the only one that accepts its
    food type), and long-lasting donations keep getting pushed back, so they can be
    starved of capacity if lots of urgent food keeps showing up.

    It doesn't change the original data, so you can run FIFO on it after.

    Returns a list with one Assignment for every donation, in the order handled.

    Time: O(D log D + D * (R + V))
    D log D is building / popping the heap, the rest is matching each donation.
    """
    donation_list = list(donations.values()) if isinstance(donations, dict) else list(donations)
    recipient_list = list(recipients.values()) if isinstance(recipients, dict) else list(recipients)
    volunteer_list = list(volunteers.values()) if isinstance(volunteers, dict) else list(volunteers)

    rec_capacity = {r["recipient_id"]: r["capacity"] for r in recipient_list}
    rec_accepts = {r["recipient_id"]: set(r["accepted_food_types"]) for r in recipient_list}
    vol_capacity = {v["volunteer_id"]: v["vehicle_capacity"] for v in volunteer_list}
    vol_pickups = {v["volunteer_id"]: v["pickup_counter"] for v in volunteer_list}

    # Arrival order is the same order FIFO uses, so we can tell when greedy jumped
    # a donation ahead of one that arrived before it
    arrived = sorted(donation_list, key=lambda d: d["ready_time"])
    heap = [(_greedy_key(d, i), i) for i, d in enumerate(arrived)]
    heapq.heapify(heap)

    results = []
    latest = -1     # latest-arriving donation handled so far
    while heap:
        _, i = heapq.heappop(heap)
        donation = arrived[i]
        assignment = _assign_one(donation, recipient_list, volunteer_list,
                                 rec_capacity, rec_accepts, vol_capacity, vol_pickups)

        # If something that arrived after this donation was already handled, it got deferred
        if latest > i:
            ahead = arrived[latest]
            assignment.reason += (f" It was deferred behind {ahead['donation_id']} under the "
                                  f"urgency-first rule because {_priority_reason(ahead, donation)}.")
        latest = max(latest, i)
        results.append(assignment)
    return results


def _assign_one(donation, recipients, volunteers,
                rec_capacity, rec_accepts, vol_capacity, vol_pickups):
    # Finds the first feasible (recipient, volunteer) pair for one donation in O(R + V)
    # and updates the capacity / pickup state on success. Shared by FIFO and greedy.
    d_id = donation["donation_id"]
    food = donation["food_type"]
    qty = donation["quantity"]
    deadline = deadline_of(donation)

    def unassigned(why):
        return Assignment(d_id, None, None, None,
                          f"Donation {d_id} could not be assigned because {why}.", "unassigned")

    # Recipients that accept this food type and still have room, in input order
    accepting = [r for r in recipients if food in rec_accepts[r["recipient_id"]]]
    if not accepting:
        return unassigned(f"no recipient accepts {food}")
    with_room = [r for r in accepting if rec_capacity[r["recipient_id"]] >= qty]
    if not with_room:
        return unassigned(f"no recipient that accepts {food} had {qty} units of remaining capacity")

    # Volunteers who can do the pickup at all. Pickup time depends only on the volunteer
    # (max of ready time and shift start), so it's computed once here.
    eligible = []
    can_carry = maxed_out = too_late = off_shift = 0
    for v in volunteers:
        v_id = v["volunteer_id"]
        if vol_capacity[v_id] < qty:
            continue
        can_carry += 1
        if vol_pickups[v_id] >= v["maximum_pickups"]:
            maxed_out += 1
            continue
        start, end = v["availability"]
        pickup = max(donation["ready_time"], start)
        if pickup > deadline:
            too_late += 1
        elif pickup > end:
            off_shift += 1
        else:
            eligible.append(v)

    if not eligible:
        if can_carry == 0:
            why = f"no volunteer had {qty} units of remaining vehicle capacity"
        elif maxed_out == can_carry:
            why = "every volunteer who could carry it had already reached their maximum pickups"
        elif off_shift == 0:
            why = (f"it expires at {_fmt_time(deadline)}, before any volunteer who could "
                   f"carry it was available")
        elif too_late == 0:
            why = (f"no volunteer who could carry it was still on shift when it was ready "
                   f"at {_fmt_time(donation['ready_time'])}")
        else:
            why = (f"no volunteer who could carry it was on shift between its ready time "
                   f"({_fmt_time(donation['ready_time'])}) and expiry ({_fmt_time(deadline)})")
        return unassigned(why)

    # A recipient can be paired with some volunteer iff it is still open at the earliest
    # possible pickup, so this picks the first recipient that has any feasible volunteer
    earliest = min(max(donation["ready_time"], v["availability"][0]) for v in eligible)
    recipient = next((r for r in with_room if r["closing_time"] >= earliest), None)
    if recipient is None:
        return unassigned(f"every recipient that accepts {food} and had room closes before "
                          f"the earliest possible pickup at {_fmt_time(earliest)}")

    # At least one eligible volunteer reaches this recipient in time (the one giving `earliest`)
    for volunteer in eligible:
        ok, pickup = check_time(donation, recipient, volunteer)
        if ok:
            break

    r_id = recipient["recipient_id"]
    v_id = volunteer["volunteer_id"]
    rec_capacity[r_id] -= qty
    vol_capacity[v_id] -= qty
    vol_pickups[v_id] += 1

    name = recipient["organization_name"]
    reason = (f"Donation {d_id} was assigned to {name} with volunteer {v_id} for pickup at "
              f"{_fmt_time(pickup)} because {name} accepts {food}, had capacity for {qty} units, "
              f"and is open until {_fmt_time(recipient['closing_time'])}, and {v_id} can carry "
              f"the quantity before the donation expires at {_fmt_time(deadline)}.")
    return Assignment(d_id, r_id, v_id, pickup, reason, "assigned")
