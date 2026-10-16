import json
import os
import tempfile
import unittest

from RescueRouter_Data import (
    _load_json as load_json,
    check_compatibility,
    check_capacity
)

from Algo import fifo_schedule, greedy_schedule, Assignment
from metrics import (compute_metrics, urgent_donation_ids, compare_metrics,
                     explain_comparison, format_comparison)


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


    def test_greedy_orders_by_expiry_then_quantity(self):
        late = dict(self.donation, donation_id="D001", ready_time=600, expire_time=300)
        soon_small = dict(self.donation, donation_id="D002", ready_time=610,
                          expire_time=90, quantity=5)
        soon_big = dict(self.donation, donation_id="D003", ready_time=620,
                        expire_time=80, quantity=10)  # same deadline as D002 (700)

        results = greedy_schedule([late, soon_small, soon_big],
                                  [self.recipient], [self.volunteer])

        self.assertEqual([a.donation_id for a in results], ["D003", "D002", "D001"])

    def test_fifo_and_greedy_differ(self):
        # Recipient only has room for one of the two; D002 arrives later but expires first
        relaxed = dict(self.donation, donation_id="D001", ready_time=600, expire_time=780)
        urgent = dict(self.donation, donation_id="D002", ready_time=610, expire_time=60)
        self.recipient["capacity"] = 30
        self.volunteer["vehicle_capacity"] = 50

        fifo = {a.donation_id: a for a in fifo_schedule(
            [relaxed, urgent], [self.recipient], [self.volunteer])}
        greedy = {a.donation_id: a for a in greedy_schedule(
            [relaxed, urgent], [self.recipient], [self.volunteer])}

        self.assertEqual(fifo["D001"].status, "assigned")
        self.assertEqual(fifo["D002"].status, "unassigned")
        self.assertEqual(greedy["D002"].status, "assigned")
        self.assertEqual(greedy["D001"].status, "unassigned")

    def test_greedy_explains_deferred_donation(self):
        # Starvation case: the long-lasting D001 arrived first but is pushed behind D002
        relaxed = dict(self.donation, donation_id="D001", ready_time=600, expire_time=780)
        urgent = dict(self.donation, donation_id="D002", ready_time=610, expire_time=60)
        self.recipient["capacity"] = 30

        results = greedy_schedule([relaxed, urgent], [self.recipient], [self.volunteer])
        deferred = results[1]

        self.assertEqual(deferred.donation_id, "D001")
        self.assertIn("deferred behind D002", deferred.reason)
        self.assertNotIn("deferred", results[0].reason)

    def test_greedy_does_not_modify_input(self):
        greedy_schedule([self.donation], [self.recipient], [self.volunteer])

        self.assertEqual(self.recipient["capacity"], 50)
        self.assertEqual(self.volunteer["vehicle_capacity"], 40)
        self.assertEqual(self.volunteer["pickup_counter"], 0)

    def test_greedy_empty_input(self):
        self.assertEqual(greedy_schedule([], [], []), [])


class TestMetrics(unittest.TestCase):
    # Hand-worked example: 4 donations, deadlines 700 / 800 / 900 / 1000.
    # Urgent = earliest 25% = ceil(4 * 0.25) = 1 donation (D001).

    def setUp(self):
        def donation(d_id, qty, deadline):
            return {"donation_id": d_id, "quantity": qty,
                    "ready_time": 600, "expire_time": deadline - 600}

        self.donations = [donation("D001", 10, 700), donation("D002", 20, 800),
                          donation("D003", 30, 900), donation("D004", 40, 1000)]
        self.recipients = [{"capacity": 50}, {"capacity": 50}]          # total 100
        self.volunteers = [{"vehicle_capacity": 30}, {"vehicle_capacity": 50}]  # total 80

    def results(self, assigned_ids):
        return [Assignment(d["donation_id"], "R001", "V001", 600, "", "assigned")
                if d["donation_id"] in assigned_ids else
                Assignment(d["donation_id"], None, None, None, "", "unassigned")
                for d in self.donations]

    def test_metrics_hand_worked_example(self):
        metrics = compute_metrics(self.results({"D001", "D003"}),
                                  self.donations, self.recipients, self.volunteers)

        self.assertEqual(metrics["donations_received"], 4)
        self.assertEqual(metrics["donations_assigned"], 2)
        self.assertEqual(metrics["donations_unassigned"], 2)
        self.assertEqual(metrics["quantity_rescued"], 40)       # 10 + 30
        self.assertEqual(metrics["quantity_at_risk"], 60)       # 20 + 40
        self.assertEqual(metrics["urgent_donations"], 1)
        self.assertAlmostEqual(metrics["urgent_rescue_rate"], 100.0)
        self.assertAlmostEqual(metrics["recipient_capacity_utilization"], 40.0)  # 40 / 100
        self.assertAlmostEqual(metrics["volunteer_capacity_utilization"], 50.0)  # 40 / 80

    def test_urgent_donation_missed(self):
        metrics = compute_metrics(self.results({"D002", "D003", "D004"}),
                                  self.donations, self.recipients, self.volunteers)

        self.assertEqual(metrics["urgent_assigned"], 0)
        self.assertAlmostEqual(metrics["urgent_rescue_rate"], 0.0)

    def test_urgent_includes_ties_at_cutoff(self):
        self.donations[1]["expire_time"] = 100   # D002 now also expires at 700

        self.assertEqual(urgent_donation_ids(self.donations), {"D001", "D002"})

    def test_metrics_empty_input(self):
        metrics = compute_metrics([], [], [], [])

        self.assertEqual(metrics["donations_received"], 0)
        self.assertEqual(metrics["quantity_rescued"], 0)
        self.assertEqual(metrics["urgent_rescue_rate"], 0.0)
        self.assertEqual(metrics["recipient_capacity_utilization"], 0.0)
        self.assertEqual(metrics["volunteer_capacity_utilization"], 0.0)

    def test_metrics_from_greedy_run(self):
        # Real run: recipient fits only one of two donations; greedy saves the urgent one
        donation = {"donor_name": "Titan Dining Hall", "food_type": "Canned Goods",
                    "quantity": 20, "location": "Center Wing"}
        relaxed = dict(donation, donation_id="D001", ready_time=600, expire_time=780)
        urgent = dict(donation, donation_id="D002", ready_time=610, expire_time=60)
        recipient = {"recipient_id": "R001", "organization_name": "Student Basic Needs Center",
                     "accepted_food_types": ["Canned Goods"], "capacity": 30,
                     "location": "Center Wing", "closing_time": 900}
        volunteer = {"volunteer_id": "V001", "vehicle_capacity": 50, "location": "Center Wing",
                     "availability": [540, 840], "maximum_pickups": 3, "pickup_counter": 0}
        args = ([relaxed, urgent], [recipient], [volunteer])

        fifo = compute_metrics(fifo_schedule(*args), *args)
        greedy = compute_metrics(greedy_schedule(*args), *args)

        self.assertAlmostEqual(fifo["urgent_rescue_rate"], 0.0)
        self.assertAlmostEqual(greedy["urgent_rescue_rate"], 100.0)
        self.assertEqual(fifo["quantity_rescued"], greedy["quantity_rescued"])


class TestComparison(unittest.TestCase):
    # Recipient fits only one of two donations. D001 arrives first, D002 expires first,
    # so FIFO assigns D001 and greedy assigns D002.

    def setUp(self):
        donation = {"donor_name": "Titan Dining Hall", "food_type": "Canned Goods",
                    "quantity": 20, "location": "Center Wing"}
        self.donations = [dict(donation, donation_id="D001", ready_time=600, expire_time=780),
                          dict(donation, donation_id="D002", ready_time=610, expire_time=60)]
        self.recipients = [{"recipient_id": "R001",
                            "organization_name": "Student Basic Needs Center",
                            "accepted_food_types": ["Canned Goods"], "capacity": 30,
                            "location": "Center Wing", "closing_time": 900}]
        self.volunteers = [{"volunteer_id": "V001", "vehicle_capacity": 50,
                            "location": "Center Wing", "availability": [540, 840],
                            "maximum_pickups": 3, "pickup_counter": 0}]

    def run_both(self):
        args = (self.donations, self.recipients, self.volunteers)
        fifo, greedy = fifo_schedule(*args), greedy_schedule(*args)
        return fifo, greedy, compute_metrics(fifo, *args), compute_metrics(greedy, *args)

    def test_compare_metrics_is_greedy_minus_fifo(self):
        _, _, fifo_m, greedy_m = self.run_both()
        diff = compare_metrics(fifo_m, greedy_m)

        self.assertEqual(diff["donations_assigned"], 0)
        self.assertEqual(diff["quantity_rescued"], 0)
        self.assertAlmostEqual(diff["urgent_rescue_rate"], 100.0)

    def test_explanation_names_changed_donations_and_why(self):
        fifo, greedy, fifo_m, greedy_m = self.run_both()
        lines = explain_comparison(fifo, greedy, fifo_m, greedy_m)
        text = " ".join(lines)

        self.assertIn("from 0.0% to 100.0%", lines[0])
        gained = next(l for l in lines if l.startswith("D002"))
        lost = next(l for l in lines if l.startswith("D001"))
        self.assertIn("only under greedy", gained)
        self.assertIn("remaining capacity", gained)       # FIFO's reason for rejecting D002
        self.assertIn("only under FIFO", lost)
        self.assertIn("deferred behind D002", lost)       # greedy's reason for rejecting D001
        self.assertNotIn("same donations", text)

    def test_explanation_when_outcomes_match(self):
        self.recipients[0]["capacity"] = 100              # room for both, order doesn't matter
        fifo, greedy, fifo_m, greedy_m = self.run_both()

        lines = explain_comparison(fifo, greedy, fifo_m, greedy_m)

        self.assertEqual(len(lines), 1)
        self.assertIn("same donations", lines[0])

    def test_format_comparison_table(self):
        _, _, fifo_m, greedy_m = self.run_both()
        table = format_comparison(fifo_m, greedy_m)

        self.assertIn("FIFO", table.splitlines()[0])
        urgent_row = next(l for l in table.splitlines() if l.startswith("Urgent rescue rate"))
        self.assertEqual(urgent_row.split()[-3:], ["0.0", "100.0", "+100.0"])


if __name__ == "__main__":
    unittest.main()