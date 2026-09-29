# Data Format
"""
List -> Dict
example:
Donations = {
    "D001": {
        "donation_id": "D001",
        "donor_name": "John Doe",
        "food_type": "Canned Goods",
        "quantity": 10,                 # to make it easier we'll go with "units" instead of pounds or kilograms
        "expire_time": 720,             # in minutes -> 12:00 PM, this is relative to the ready time
        "location": "Cafeteria",     
        "ready_time": 380               # in minutes -> 6:20 AM, this is absolute time from midnight which is 0
    },
}

Recipients = {
    "R001":{
        "recipient_id": "R001",
        "organization_name": "Helping Hands",
        "accepted_food_types": {"Canned Goods", "Fresh Produce"},
        "capacity": 50,                                                 # units of food
        "location": "Computer Science Building",
        "closing_time": 1020                                            # in minutes, e.g., 1020 minutes = 5:00 PM absolute time from midnight which is 0
    },
}       

Volunteers = {
    "V001": {
        "volunteer_id": "V001",
        "vehicle_capacity": 50,                # in units of food
        "location": "Cafeteria",     # initial location of the volunteer
        "availability": [480, 1020],           # in minutes, e.g., 480 = 8:00 AM, 1020 = 5:00 PM
        "maximum_pickups": 5,                  # maximum number of pickups the volunteer can handle
        "pickup_counter": 0,                   # current number of pickups the volunteer has made
    },
}
"""

#formats the txt data into python list dict system
def load_donations(path):
    return

# compatibility checks [compares hard values like food type, capacity, and availability]
def check_compatibility(donation, recipient, volunteer):
    # Hard checks
    # if the recipient cannot accept food type, reject
    # if the recipient does not have enough capacity, reject
    # if the donation is not at the same location as the volunteer and recipient, reject
    # if the volunteer has reached their maximum number of pickups, reject
    # if the donation has already expired, reject
    # if the donation is not ready before volunteer shift ends, reject
    if donation["food_type"] not in recipient["accepted_food_types"]:
        return False
    if donation["quantity"] > recipient["capacity"]:
        return False
    if not (donation["location"] == volunteer["location"] == recipient["location"]):
        return False
    if volunteer["pickup_counter"] >= volunteer["maximum_pickups"]:
        return False
    if donation["expire_time"] <= 0:
        return False
    if donation["ready_time"] > volunteer["availability"][1]:
        return False
    #time logic
    #if donation is ready after closing time of recipient, it's not compatible
    #if donation expires before the volunteer can pick it up, it's not compatible
    #if volunteer cannot initially pick it up but can pick it up before food expires -> check if vounteer min time is before closing time
    if donation["ready_time"] > recipient["closing_time"]:
        return False
    if donation["ready_time"] + donation["expire_time"] < volunteer["availability"][0]:
        return False
    if volunteer["availability"][0] > recipient["closing_time"]:
        return False
    return True

# capacity checks [compares the capacity of recipients and vehicle capacity of volunteers]

def check_capacity(donation, recipient, volunteer):
    if donation["quantity"] > recipient["capacity"]:
        return False
    if donation["quantity"] > volunteer["vehicle_capacity"]:
        return False
    return True