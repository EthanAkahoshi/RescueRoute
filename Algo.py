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
