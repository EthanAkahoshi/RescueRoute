# RescueRouter Data Handling Module
# This module provides functions to handle and check the compatibility and capacity of donations, recipients, and volunteers.
#formats the txt data into python list dict system
import json
def load_json(filepath, required_fields):
    valid_entries = {}

    try:
    # Open the JSON file and load contents
    # with how hashmaps work duplicate keys will be overwritten. adding separate comparisons for duplicates is costly and will not be implemented
        with open(filepath, 'r') as file:
            data = json.load(file)

    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return valid_entries

    # Iterate through each entry in JSON data
    for key, entry in data.items():
        is_valid = True

        # Check if all required fields are present and not empty
        for field in required_fields:
            val = entry.get(field)

            if val is None or val == "" or val == []:
                print(f"Missing or empty required field '{field}' in entry with key '{key}'")
                is_valid = False
                break

        if is_valid:
            valid_entries[key] = entry

    return valid_entries

def load_all_data():
    donations = load_json("./input_data/donations.json", ["donation_id", "donor_name", "food_type", "quantity", "expire_time", "location", "ready_time"])
    recipients = load_json("./input_data/recipients.json", ["recipient_id", "organization_name", "accepted_food_types", "capacity", "location", "closing_time"])
    volunteers = load_json("./input_data/volunteers.json", ["volunteer_id", "vehicle_capacity", "location", "availability", "maximum_pickups", "pickup_counter"])
    
    return donations, recipients, volunteers
    #returning as a tuple so you can just do donations, recipients, volunteers = load_all_data()


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
