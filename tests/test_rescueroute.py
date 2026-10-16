import json
import os
import tempfile
import unittest

from RescueRouter_Data import (
    _load_json as load_json,
    check_compatibility,
    check_capacity
)

from Algo import fifo_schedule


class TestRescueRouteData(unittest.TestCase):

    def setUp(self):
        # Valid donation used as the starting point for each test
        self.donation = {
            "donation_id": "D001",
            "donor_name": "Titan Dining Hall",
            "food_type": "Canned Goods",
            "quantity": 20,
            "expire_time": 780,
            "location": "Center Wing",
            "ready_time": 600
        }

        # Valid recipient used as the starting point for each test
        self.recipient = {
            "recipient_id": "R001",
            "organization_name": "Student Basic Needs Center",
            "accepted_food_types": ["Canned Goods", "Fresh Produce"],
            "capacity": 50,
            "location": "Center Wing",
            "closing_time": 900
        }

        # Valid volunteer used as the starting point for each test
        self.volunteer = {
            "volunteer_id": "V001",
            "vehicle_capacity": 40,
            "location": "Center Wing",
            "availability": [540, 840],
            "maximum_pickups": 3,
            "pickup_counter": 0
        }

    def test_valid_compatibility(self):
        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertTrue(result)

    def test_incompatible_food_type(self):
        self.donation["food_type"] = "Prepared Meals"

        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_location_mismatch(self):
        self.volunteer["location"] = "North Wing"

        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_volunteer_maximum_pickups_reached(self):
        self.volunteer["pickup_counter"] = 3

        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_donation_expires_before_volunteer_available(self):
        self.donation["ready_time"] = 500
        self.donation["expire_time"] = 20

        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_recipient_closed_before_donation_ready(self):
        self.recipient["closing_time"] = 590

        result = check_compatibility(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_valid_capacity(self):
        result = check_capacity(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertTrue(result)

    def test_recipient_capacity_too_small(self):
        self.recipient["capacity"] = 10

        result = check_capacity(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_vehicle_capacity_too_small(self):
        self.volunteer["vehicle_capacity"] = 10

        result = check_capacity(
            self.donation,
            self.recipient,
            self.volunteer
        )

        self.assertFalse(result)

    def test_load_json_valid_entry(self):
        test_data = [
            {
                "donation_id": "D001",
                "quantity": 20
            }
        ]

        with tempfile.TemporaryDirectory() as temp_directory:
            filepath = os.path.join(temp_directory, "test.json")

            with open(filepath, "w") as file:
                json.dump(test_data, file)

            result = load_json(
                filepath,
                ["donation_id", "quantity"]
            )

            self.assertIn("D001", result)

    def test_load_json_missing_required_field(self):
        test_data = [
            {
                "donation_id": "D001",
                "quantity": 20
            },
            {
                "donation_id": "D002"
            }
        ]

        with tempfile.TemporaryDirectory() as temp_directory:
            filepath = os.path.join(temp_directory, "test.json")

            with open(filepath, "w") as file:
                json.dump(test_data, file)

            result = load_json(
                filepath,
                ["donation_id", "quantity"]
            )

            self.assertIn("D001", result)
            self.assertNotIn("D002", result)

    def test_missing_json_file(self):
        result = load_json(
            "file_that_does_not_exist.json",
            ["donation_id"]
        )

        self.assertEqual(result, {})

    def test_duplicate_donation_id(self):
        test_data = [
            {
                "donation_id": "D001",
                "quantity": 20
            },
            {
                "donation_id": "D001",
                "quantity": 30
            }
        ]

        with tempfile.TemporaryDirectory() as temp_directory:
            filepath = os.path.join(temp_directory, "test.json")

            with open(filepath, "w") as file:
                json.dump(test_data, file)

            result = load_json(
                filepath,
                ["donation_id", "quantity"]
            )

            self.assertEqual(len(result), 1)
            self.assertIn("D001", result)
            self.assertEqual(result["D001"]["quantity"], 20)
    
    def test_two_donations_competing_for_capacity(self):
        first_donation = self.donation.copy()

        second_donation = self.donation.copy()
        second_donation["donation_id"] = "D002"
        second_donation["ready_time"] = 610

        self.recipient["capacity"] = 30
        self.volunteer["vehicle_capacity"] = 50

        results = fifo_schedule(
            [first_donation, second_donation],
            [self.recipient],
            [self.volunteer]
        )

        self.assertEqual(len(results), 2)

        self.assertEqual(results[0].donation_id, "D001")
        self.assertEqual(results[0].status, "assigned")
        self.assertEqual(results[0].recipient_id, "R001")

        self.assertEqual(results[1].donation_id, "D002")
        self.assertEqual(results[1].status, "unassigned")
        self.assertIsNone(results[1].recipient_id)
        self.assertIn("remaining capacity", results[1].reason.lower())

        self.assertEqual(self.recipient["capacity"], 30)

    
    def test_empty_input_lists(self):
        results = fifo_schedule(
            [],
            [],
            []
        )

        self.assertEqual(results, [])

        
    def test_fifo_successful_assignment(self):
        results = fifo_schedule(
            [self.donation],
            [self.recipient],
            [self.volunteer]
        )

        self.assertEqual(len(results), 1)

        assignment = results[0]

        self.assertEqual(assignment.donation_id, "D001")
        self.assertEqual(assignment.recipient_id, "R001")
        self.assertEqual(assignment.volunteer_id, "V001")
        self.assertEqual(assignment.status, "assigned")
        self.assertEqual(assignment.scheduled_time, 600)

        self.assertIn("Student Basic Needs Center", assignment.reason)
        self.assertIn("Canned Goods", assignment.reason)
        self.assertIn("capacity", assignment.reason.lower())


if __name__ == "__main__":
    unittest.main()