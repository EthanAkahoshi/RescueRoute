# RescueRouter Data Handling Module
# This module provides functions to handle and check the compatibility and capacity of donations, recipients, and volunteers.
#formats the txt data into python list dict system
import json
def _load_json(filepath, required_fields):
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
    donations = _load_json("./input_data/donations.json", ["donation_id", "donor_name", "food_type", "quantity", "expire_time", "location", "ready_time"])
    recipients = _load_json("./input_data/recipients.json", ["recipient_id", "organization_name", "accepted_food_types", "capacity", "location", "closing_time"])
    volunteers = _load_json("./input_data/volunteers.json", ["volunteer_id", "vehicle_capacity", "location", "availability", "maximum_pickups", "pickup_counter"])
    
    return donations, recipients, volunteers
    #returning as a tuple so you can just do donations, recipients, volunteers = load_all_data()


# compatibility checks [compares hard values like food type, capacity, and availability]
def check_compatibility(donation, recipient, volunteer):
    # HARD CHECKS

    # if the recipient cannot accept food type, reject
    if donation["food_type"] not in recipient["accepted_food_types"]:
        return False
    # if the donation is not at the same location as the volunteer and recipient, reject
    if not (donation["location"] == volunteer["location"] == recipient["location"]):
        return False
    # if the volunteer has reached their maximum number of pickups, reject
    if volunteer["pickup_counter"] >= volunteer["maximum_pickups"]:
        return False
    
    #TIME CHECKS

    # if the donation has already expired, reject
    if (donation["ready_time"] + donation["expire_time"]) <= volunteer["availability"][0]:
        return False
    # if the donation is not ready before volunteer shift ends, reject
    if donation["ready_time"] >= volunteer["availability"][1]:
        return False
    # if the donation is not ready before recipient closing time, reject
    if donation["ready_time"] >= recipient["closing_time"]:
        return False
    # if the volunteer shift starts after recipient closing time, reject
    if volunteer["availability"][0] >= recipient["closing_time"]:
        return False
    
    return True

# CAPACITY CHECKS [compares the capacity of recipients and vehicle capacity of volunteers]

def check_capacity(donation, recipient, volunteer):
    if donation["quantity"] > recipient["capacity"]:
        return False
    if donation["quantity"] > volunteer["vehicle_capacity"]:
        return False
    return True
