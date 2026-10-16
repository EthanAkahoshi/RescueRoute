# RescueRoute

RescueRoute is a command-line Python application that matches time-sensitive surplus food donations with compatible recipient organizations and volunteer drivers. It compares a **FIFO baseline** with a **greedy urgency-first strategy** on the same input data, explains every assignment, rejection, and deferral in plain English, and reports metrics for both strategies.

> **Disclaimer:** RescueRoute is an educational prototype for CPSC 335 that uses simulated data. It is not food-safety certified, clinically validated, approved for emergency operations, or ready for real-world operational deployment.

## Setup and Running
Requirements: Python 3.8 or newer (developed on Python 3.14). Only the standard library is used, so there is nothing to install.

```
git clone https://github.com/EthanAkahoshi/RescueRoute.git
cd RescueRoute
python main.py
```

`main.py` loads the files in `input_data/`, validates them, then prints for each strategy:
1. one explanation per donation (`[assigned]` or `[unassigned]`, with deferrals noted under greedy),
2. the metrics block,

and finally a FIFO vs. greedy comparison table followed by an explanation of what changed and why. To try other data, edit the JSON files in `input_data/`; invalid entries are reported and skipped.

Run the tests with `python -m unittest discover -s tests -v` (see [Running the Unit Tests](#running-the-unit-tests)).

## Architecture
```
input_data/*.json --> RescueRouter_Data.load_all_data   (parse JSON, drop missing fields / duplicate IDs)
                  --> validation.validate_all            (drop entries with invalid values)
                  --> Algo.fifo_schedule / greedy_schedule
                        both call Algo._assign_one --> check_compatibility + check_capacity
                  --> metrics.compute_metrics            (per strategy)
                  --> metrics.format_comparison / explain_comparison
```

| File | Responsibility |
|---|---|
| `main.py` | Entry point: runs the pipeline above and prints the results |
| `RescueRouter_Data.py` | JSON loading, missing-field and duplicate-ID checks, `check_compatibility`, `check_capacity` |
| `validation.py` | Value validation (types, ranges, known food types and locations) |
| `Algo.py` | `Assignment` record, FIFO and greedy schedulers, shared matching step, explanations |
| `metrics.py` | Metrics, FIFO vs. greedy comparison table, and comparison explanation |
| `input_data/` | Sample donations, recipients, and volunteers (10 each, simulated) |
| `tests/test_rescueroute.py` | Automated unit tests |

## Data Model
All times are **minutes from midnight** (480 = 8:00 AM). Quantities and capacities are in generic food **units**.

| Entity | Fields |
|---|---|
| Donation | `donation_id`, `donor_name`, `food_type`, `quantity`, `expire_time` (minutes after `ready_time` until it expires), `location` (pickup area), `ready_time` |
| Recipient | `recipient_id`, `organization_name`, `accepted_food_types`, `capacity`, `location`, `closing_time` |
| Volunteer | `volunteer_id`, `vehicle_capacity`, `location`, `availability` (`[start, end]` shift), `maximum_pickups`, `pickup_counter` (pickups already made) |
| Assignment | `donation_id`, `recipient_id`, `volunteer_id`, `scheduled_time` (pickup time), `reason` (explanation), `status` (`assigned` / `unassigned`) |

Food types: Prepared Meals, Fresh Produce, Canned Goods, Baked Goods. Locations: North Wing, South Wing, Center Wing.

| Need | Data structure | Why |
|---|---|---|
| Entities by ID | `dict` | O(1) lookup by ID |
| Duplicate-ID detection | `set` | O(1) membership test while loading |
| Accepted food types | `set` (converted during validation) | O(1) check of whether a recipient accepts a food type |
| FIFO processing | `collections.deque` | Preserves arrival order, O(1) pop from the front |
| Greedy pending donations | `heapq` priority queue | O(log D) to take the next most urgent donation |
| Remaining capacity / pickups | `dict` keyed by ID | Updated per assignment without modifying the input data |
| Assignment history | `list` of `Assignment` | Ordered audit trail of decisions |
| Metrics | `dict` | Named aggregate values |

## Data Architecture & Ingestion
The system relies on JSON files (`donations.json`, `recipients.json`, `volunteers.json`) to simulate the operational environment. 
* O(1) Lookups: All entities are loaded into Python dictionaries keyed by their respective IDs (ex: "donation_id"). This ensures that the scheduling algorithms can retrieve entity data in constant time.
* Validation: "_load_json" function checks incoming data. It actively drops entries containing missing or empty fields (such as empty strings or null arrays) to prevent crashes and also checks for duplicates using a set.

## Validation
After loading, `validation.validate_all` checks every value and drops any entry that breaks a rule, printing one message that lists every problem with that entry (e.g. `Donation D003 rejected: quantity must be a whole number of at least 1 (got -5)`).

| Entity | Rules |
|---|---|
| Donation | ID and donor name are non-empty text; `food_type` and `location` are known values; `quantity` and `expire_time` are whole numbers of at least 1; `ready_time` is 0-1440 |
| Recipient | ID and name are non-empty text; `accepted_food_types` is a non-empty list of known types; `capacity` is a whole number of at least 0; `location` is known; `closing_time` is 0-1440 |
| Volunteer | ID is non-empty text; `vehicle_capacity`, `maximum_pickups`, and `pickup_counter` are whole numbers of at least 0; `location` is known; `availability` is `[start, end]` with 0 <= start < end <= 1440 |

The loader also treats blank, malformed, or non-list JSON files as empty (with a message) instead of crashing.

## Matching Engine & Constraints
Before the scheduler prioritizes a donation, the system evaluates feasibility using a boolean check. A match is only considered valid if it passes two constraint categories:
1. Hard Constraints: The volunteer must not exceed their "maximum_pickups" limit, the food quantity must not exceed the volunteer's "vehicle_capacity" or the recipient's "capacity", and the recipient's "accepted_food_types" match the donation's "food_type". All three entities must also share the same "location".
2. Static Time Overlap: To avoid the complexity of a simulated clock, the system calculates overlaps using absolute minutes from midnight (ex: 8:00 AM = 480). 
   * "ready_time", "closing_time", and volunteer "availability" uses absolute time as stated above.
   * "expire_time" is calculated relative to the ready time. (ex: expire time of 60 with ready time of 60 means ready at 1:00 AM and expires at 2:00 AM)

## Scheduling Strategies
Both strategies live in `Algo.py` and use the same matching step: for each donation they take the first recipient and volunteer pair that passes `check_compatibility` and `check_capacity` from `RescueRouter_Data.py`, using the remaining capacity and pickup counts at that moment. They only differ in the **order** donations are handled, so the comparison is fair.

### A. FIFO baseline (`fifo_schedule`)
Donations are handled in arrival order (earliest `ready_time` first) using a `deque`.

### B. Greedy urgency-first (`greedy_schedule`)
**Greedy rule:** First schedule the donation with the earliest expiry deadline (`ready_time + expire_time`). If two donations expire at the same time, schedule the larger quantity first. If still tied, schedule the one with the earlier `ready_time`, then the one that arrived first.

* Data structure: a `heapq` priority queue keyed by `(deadline, -quantity, ready_time, arrival_position)`.
* What it optimizes locally: food closest to going bad gets first pick of recipient capacity and volunteers.
* Trade-offs / where it fails: it does not look ahead, so an urgent donation can use up capacity that a later donation needed more (e.g. the only recipient accepting its food type). Long-lasting donations are repeatedly pushed back and can be starved of capacity when lots of urgent food arrives. Every deferred donation's explanation names the donation it was deferred behind and why.

### Complexity
Let D = donations, R = recipients, V = volunteers. Both strategies run in **O(D log D + D·R·V)**: the D log D comes from sorting (FIFO) or the heap (greedy), and matching each donation tries every recipient / volunteer pair in the worst case (each pair check is O(1) once accepted food types are a set). Validation is O(D + R + V) and metrics are O(D log D + R + V), so scheduling dominates. For the sample data (D = R = V = 10) that is at most 1,000 pair checks per strategy.

## Metrics
`metrics.compute_metrics` calculates the following for each strategy:

| Metric | Definition |
|---|---|
| Donations received | Number of valid donation records processed |
| Donations assigned / unassigned | Donations matched to a recipient and volunteer / left without a feasible match |
| Food quantity rescued | Total quantity of assigned donations |
| Food quantity at risk | Total quantity of unassigned donations |
| Urgent rescue rate | Percentage of urgent donations that were assigned. **Urgent = the earliest-expiring 25% of donations by deadline** (`ready_time + expire_time`), rounded up, plus any donation tied with the last one. Set by `URGENT_FRACTION` in `metrics.py`. |
| Recipient capacity utilization | Quantity rescued / total starting capacity of all recipients |
| Volunteer capacity utilization | Quantity rescued / total starting vehicle capacity of all volunteers |

## FIFO vs. Greedy Comparison
Results on the sample data in `input_data/` (output of `python main.py`):

| Metric | FIFO | Greedy | Difference |
|---|---|---|---|
| Donations assigned | 7 | 7 | 0 |
| Donations unassigned | 3 | 3 | 0 |
| Food quantity rescued | 185 | 190 | +5 |
| Food quantity at risk | 100 | 95 | -5 |
| Urgent rescue rate | 66.7% | 100.0% | +33.3 pts |
| Recipient utilization | 30.8% | 31.7% | +0.8 pts |
| Volunteer utilization | 43.0% | 44.2% | +1.2 pts |

**What changed and why.** Both strategies use identical matching rules, so the only difference is processing order. D004 (30 units of fresh produce, expires 1:00 AM) and D007 (35 units of fresh produce, expires 3:00 PM) both need the only North Wing recipient that accepts produce, Senior Citizens Center, which has room for 45 units.
* **FIFO** handles D004 first because it was ready earlier (11:00 AM vs. 1:00 PM). It takes 30 units of capacity, so D007, the most urgent donation in the data set, is rejected.
* **Greedy** handles D007 first because it expires sooner, so D007 is rescued and D004 is rejected instead.

Greedy therefore rescues the urgent donation (urgent rescue rate 66.7% to 100%) and 5 more units of food, with the same number of donations assigned. The other two unassigned donations fail under both strategies for reasons processing order cannot fix: D009 has no Center Wing volunteer with a large enough vehicle, and D010 has no volunteer on shift in time.

## Fairness and Starvation
Greedy urgency-first is not fair to long-lasting donations. In the comparison above, D004 was ready two hours before D007 and would have been rescued under FIFO, but greedy deferred it behind D007 and it lost its only possible recipient. Its explanation says so directly: *"It was deferred behind D007 under the urgency-first rule because D007 expires at 3:00 PM, before D004 expires at 1:00 AM the next day."* The `test_greedy_explains_deferred_donation` test checks this behavior.

If urgent donations keep arriving, a donation with a long shelf life can be pushed back every time until all compatible capacity is gone, which is starvation. We accept this trade-off because a long-lasting donation can often be picked up later or by another organization, while an urgent one is lost if it is not handled now. Possible mitigations (not implemented) include reserving a share of capacity for older donations, or raising a donation's priority the longer it waits (aging).

## Limitations and Assumptions
* **The whole day is planned at once.** Both strategies see every donation up front, including ones that become ready later. Greedy can therefore defer a donation that is ready at 8:00 AM behind one that is not ready until 1:00 PM; the 8:00 AM pickup time itself is unchanged. A real-time version would only consider donations that are already ready.
* **Vehicle capacity is a total for the day**, not per trip: a volunteer with a 40-unit vehicle can carry 40 units across all of their pickups combined.
* **No travel time or distance.** Pickup time is the later of the donation's ready time and the volunteer's shift start, and delivery is assumed to happen before the recipient closes. Matching requires all three parties to be in the same location.
* **First feasible match, not best match.** Each donation takes the first recipient and volunteer pair that works, in input order, which can use up capacity another donation needed more. Neither strategy is globally optimal.
* **Fixed categories.** Food types and locations must exactly match the known lists (case-sensitive).
* **Simulated data only.** All sample data is invented for this project.

## Automated Testing
RescueRoute uses Python's built-in unittest framework to verify the correctness and reliability of its scheduling functionality.
Unit tests are located in the tests directory, primarily within test_rescueroute.py.

## Running the Unit Tests
From the project's root directory, execute:
python -m unittest discover -s tests -v
This command discovers and executes the available unit tests and displays their results.

## References
* Python standard library documentation (https://docs.python.org/3/library/): `heapq`, `collections.deque`, `dataclasses`, `json`, `unittest`, `tempfile`.
* CPSC 335 RescueRoute Group Project Brief (project requirements and example greedy rule).
* No external libraries, datasets, or third-party code were used.

## Team Contributions
* [Kihyun Won] (Data & Matching Lead): 
    - Built the Json data retriever with duplicate and missing data checks during initial data load as well as the comparison logic for feasability checks between entities.
    - Designed the data format for the various entities to be used in the program.

* [Elias Zoreikat] (Product & Quality Lead):
   - Developed automated unit tests to verify the functionality of the RescueRoute scheduling algorithms.

   - Tested successful FIFO assignments, empty input scenarios, and assignment data accuracy.

   - Improved project documentation by explaining the testing process, scheduling algorithms, and application limitations.

   - Assisted with debugging and verifying expected program behavior.

* [Ethan Akahoshi] (Algorithm & Optimization Lead):
   - Set up the GitHub repository and the initial donation and pickup-time logic (`deadline_of` and the original pickup-time check).

   - Implemented the FIFO baseline scheduler with explainable assignment and rejection messages, and connected it to the input data in `main.py`.

   - Implemented the greedy urgency-first scheduler (`heapq` priority queue keyed on expiry deadline, quantity, and ready time), sharing FIFO's matching step so the two strategies differ only in processing order.

   - Added deferral explanations showing which donation went ahead under the greedy rule and why.

   - Wrote the greedy unit tests (priority ordering, FIFO vs. greedy producing different results, deferral/starvation, input not modified, empty input).

   - Documented the greedy rule, its trade-offs, and the complexity analysis in this README.

   - Added the metrics module (urgent rescue rate, capacity utilization, quantity rescued / at risk) and the FIFO vs. greedy comparison table and explanation.

   - Added value validation for donations, recipients, and volunteers, and fixed the loader crash on blank or malformed JSON files.

   - Updated the sample data to include a FIFO vs. greedy competition case, and expanded this README (setup, architecture, data model, metrics, comparison results, fairness, limitations, references).
