#donations (Time that the food is good)
#recipents (Can only take certain food and closes at certain times)
#volunteers (Works certain hours and can only do certain trips)

#Two ways to handle this:
#FIFO Handle donations as they arrive
#greedy urgency handle dontations in a way that donations that expeires first gets delievered

def deadline_of(donation):
    return donation["ready_time"] + donation["expire_time"]