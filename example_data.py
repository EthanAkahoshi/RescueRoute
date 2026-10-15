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