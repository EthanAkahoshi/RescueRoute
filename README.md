# RescueRoute

RescueRoute is our CPSC 335 group project. It's a command-line Python program that takes surplus food donations and tries to match each one with a recipient organization (shelters, pantries, etc.) and a volunteer driver who can pick it up. We run two scheduling strategies on the same data, a FIFO baseline and a greedy "most urgent first" strategy, and compare how they do. The program also prints an explanation for every decision so you can see why each donation was or wasn't assigned.

**Note:** This is a school project that uses made-up data. It is not food-safety certified or meant to be used for real food pickups or emergencies.

## How to Run It
You need Python 3.8 or newer (we used 3.14). Everything we used is in the standard library, so you don't have to install anything.

```
git clone https://github.com/EthanAkahoshi/RescueRoute.git
cd RescueRoute
python main.py
```

When you run `main.py` it loads the JSON files in `input_data/`, checks them for bad values, and then for FIFO and then greedy it prints:
1. a line for every donation saying if it was assigned or not and why
2. the metrics for that strategy

At the end it prints a table comparing FIFO and greedy, plus a few sentences explaining what was different between them. If you want to try your own data you can edit the JSON files. Anything invalid gets skipped and the program tells you why.

To run the tests: `python -m unittest discover -s tests -v` (more on this below).

## How the Code Is Organized
This is the order the program runs in:

```
input_data/*.json --> RescueRouter_Data.load_all_data   (parse JSON, drop missing fields / duplicate IDs)
                  --> validation.validate_all            (drop entries with invalid values)
                  --> Algo.fifo_schedule / greedy_schedule
                        both call Algo._assign_one --> check_compatibility + check_capacity
                  --> metrics.compute_metrics            (per strategy)
                  --> metrics.format_comparison / explain_comparison
```

| File | What it does |
|---|---|
| `main.py` | Runs everything above and prints the output |
| `RescueRouter_Data.py` | Loads the JSON files, removes duplicates and missing fields, and has `check_compatibility` and `check_capacity` |
| `validation.py` | Checks that the values make sense (numbers in range, real food types, real locations, etc.) |
| `Algo.py` | The FIFO and greedy schedulers, the `Assignment` class, and the explanations |
| `metrics.py` | Calculates the metrics and builds the FIFO vs. greedy comparison |
| `input_data/` | Our sample data: 10 donations, 10 recipients, 10 volunteers (all made up) |
| `tests/test_rescueroute.py` | Our unit tests |

## Data Model
All times are in minutes from midnight, so 480 means 8:00 AM. Quantities are just "units" of food to keep things simple.

| Entity | Fields |
|---|---|
| Donation | `donation_id`, `donor_name`, `food_type`, `quantity`, `expire_time` (how many minutes after `ready_time` it goes bad), `location`, `ready_time` |
| Recipient | `recipient_id`, `organization_name`, `accepted_food_types`, `capacity`, `location`, `closing_time` |
| Volunteer | `volunteer_id`, `vehicle_capacity`, `location`, `availability` (`[start, end]` of their shift), `maximum_pickups`, `pickup_counter` |
| Assignment | `donation_id`, `recipient_id`, `volunteer_id`, `scheduled_time` (pickup time), `reason`, `status` (`assigned` or `unassigned`) |

The food types are Prepared Meals, Fresh Produce, Canned Goods, and Baked Goods. The locations are North Wing, South Wing, and Center Wing.

Data structures we used and why:
* **dict** for storing donations, recipients, and volunteers by ID, so looking one up is O(1)
* **set** for catching duplicate IDs and for each recipient's accepted food types (O(1) to check if they take something)
* **deque** for FIFO since it keeps arrival order and popping from the front is O(1)
* **heapq** for greedy so we can always grab the most urgent donation in O(log D)
* **dict** for keeping track of remaining capacity and pickup counts, so we never change the original data
* **list** for the assignment history, and a **dict** for the metrics

## Data Architecture & Ingestion
The system relies on JSON files (`donations.json`, `recipients.json`, `volunteers.json`) to simulate the operational environment. 
* O(1) Lookups: All entities are loaded into Python dictionaries keyed by their respective IDs (ex: "donation_id"). This ensures that the scheduling algorithms can retrieve entity data in constant time.
* Validation: "_load_json" function checks incoming data. It actively drops entries containing missing or empty fields (such as empty strings or null arrays) to prevent crashes and also checks for duplicates using a set.

## Validation
After the data is loaded, `validation.validate_all` goes through every entry and throws out anything with a bad value. It prints a message listing everything that was wrong with it, like `Donation D003 rejected: quantity must be a whole number of at least 1 (got -5)`.

What it checks:
* **Donations:** ID and donor name can't be blank, food type and location have to be ones we know, quantity and expire time have to be whole numbers of at least 1, and ready time has to be between 0 and 1440
* **Recipients:** ID and name can't be blank, accepted food types has to be a non-empty list of real food types, capacity can't be negative, location has to be real, and closing time has to be between 0 and 1440
* **Volunteers:** ID can't be blank, vehicle capacity / max pickups / pickup counter can't be negative, location has to be real, and availability has to be `[start, end]` where start comes before end and both are between 0 and 1440

The loader also doesn't crash anymore if a JSON file is blank or broken. It just prints a message and treats it as empty.

## Matching Engine & Constraints
Before the scheduler prioritizes a donation, the system evaluates feasibility using a boolean check. A match is only considered valid if it passes two constraint categories:
1. Hard Constraints: The volunteer must not exceed their "maximum_pickups" limit, the food quantity must not exceed the volunteer's "vehicle_capacity" or the recipient's "capacity", and the recipient's "accepted_food_types" match the donation's "food_type". All three entities must also share the same "location".
2. Static Time Overlap: To avoid the complexity of a simulated clock, the system calculates overlaps using absolute minutes from midnight (ex: 8:00 AM = 480). 
   * "ready_time", "closing_time", and volunteer "availability" uses absolute time as stated above.
   * "expire_time" is calculated relative to the ready time. (ex: expire time of 60 with ready time of 60 means ready at 1:00 AM and expires at 2:00 AM)

## Scheduling Strategies
Both strategies are in `Algo.py`. They use the exact same matching step: for each donation, go through the recipients and volunteers and take the first pair that passes `check_compatibility` and `check_capacity` (using how much capacity is left at that point). The only thing that's different between them is the order the donations get handled in, so it's a fair comparison.

### A. FIFO (`fifo_schedule`)
Handles donations in the order they arrive (earliest `ready_time` first) using a deque.

### B. Greedy urgency-first (`greedy_schedule`)
**Our greedy rule:** Schedule the donation with the earliest expiration deadline first (deadline = `ready_time + expire_time`). If two donations expire at the same time, do the bigger quantity first. If they're still tied, do the one with the earlier `ready_time`, and if that's tied too, the one that showed up first in the list.

We use `heapq` with the key `(deadline, -quantity, ready_time, arrival_position)` to get this order.

**What it optimizes locally:** the food that's about to go bad gets first pick of recipients and volunteers. We think this makes sense because food that lasts a long time can usually wait or go somewhere else, but urgent food is just gone if nobody takes it.

**Where it can fail:** it doesn't look ahead. An urgent donation might take a spot that a later donation needed more (like if that recipient was the only one that accepts its food type). Also, donations that last a long time keep getting pushed back, so if a lot of urgent food shows up they might never get assigned. Whenever greedy pushes a donation back, the explanation says which donation went ahead of it and why.

### Complexity
Let D = number of donations, R = recipients, V = volunteers.

Both strategies are **O(D log D + D·R·V)**. The D log D part is from sorting (FIFO) or the heap (greedy). The D·R·V part is because for each donation, in the worst case we try every recipient/volunteer pair, and each check is O(1). Validation is O(D + R + V) and the metrics are O(D log D + R + V), so the scheduling is the slowest part. For our sample data (10 of each) that's at most 1,000 pair checks per strategy, which runs instantly.

## Metrics
`metrics.compute_metrics` calculates these for each strategy:

| Metric | How we calculate it |
|---|---|
| Donations received | Number of valid donations |
| Donations assigned / unassigned | How many got matched / how many didn't |
| Food quantity rescued | Total quantity of the assigned donations |
| Food quantity at risk | Total quantity of the unassigned donations |
| Urgent rescue rate | Percent of urgent donations that got assigned. We count the earliest-expiring 25% of donations as urgent (rounded up, plus any that tie with the last one). You can change this with `URGENT_FRACTION` in `metrics.py`. |
| Recipient capacity utilization | Food rescued / total capacity of all recipients |
| Volunteer capacity utilization | Food rescued / total vehicle capacity of all volunteers |

## FIFO vs. Greedy Results
This is what `python main.py` gives on our sample data:

| Metric | FIFO | Greedy | Difference |
|---|---|---|---|
| Donations assigned | 7 | 7 | 0 |
| Donations unassigned | 3 | 3 | 0 |
| Food quantity rescued | 185 | 190 | +5 |
| Food quantity at risk | 100 | 95 | -5 |
| Urgent rescue rate | 66.7% | 100.0% | +33.3 |
| Recipient utilization | 30.8% | 31.7% | +0.8 |
| Volunteer utilization | 43.0% | 44.2% | +1.2 |

**Why they're different:** It all comes down to D004 and D007. They're both fresh produce in North Wing, and the only North Wing recipient that takes produce is Senior Citizens Center, which only has room for 45 units. D004 is 30 units and D007 is 35, so only one of them fits.
* **FIFO** does D004 first because it was ready earlier (11:00 AM vs 1:00 PM). That leaves only 15 units of space, so D007 gets rejected even though it's the most urgent donation in the whole data set (it expires at 3:00 PM).
* **Greedy** does D007 first because it expires first. So D007 gets rescued and D004 gets rejected instead.

That's why greedy has a 100% urgent rescue rate and saves 5 more units, even though both assign 7 donations. The other two unassigned donations fail no matter what order you use: D009 needs 50 units and no Center Wing volunteer has a big enough car, and D010 doesn't have any volunteer on shift in time.

## Fairness and Starvation
Greedy isn't fair to donations that last a long time. In our results, D004 was ready two hours before D007 and would have been picked up under FIFO, but greedy pushed it back and it lost its only possible recipient. The program explains this: *"It was deferred behind D007 under the urgency-first rule because D007 expires at 3:00 PM, before D004 expires at 1:00 AM the next day."* We test this in `test_greedy_explains_deferred_donation`.

If urgent donations keep showing up, a long-lasting donation could get pushed back over and over until there's no room left anywhere. That's starvation. We decided this is an okay trade-off because losing urgent food is worse, but a couple of ways to fix it would be saving some capacity for older donations, or slowly raising a donation's priority the longer it waits (aging). We didn't implement either of these.

## Limitations
* **We plan the whole day at once.** Both strategies can see every donation from the start, even ones that won't be ready until later. So greedy can "defer" a donation that's ready at 8:00 AM behind one that isn't ready until 1:00 PM (the 8:00 AM pickup still happens at 8:00 AM though). A real system would only know about donations that are already ready.
* **Vehicle capacity is for the whole day**, not per trip. A volunteer with a 40-unit car can only carry 40 units total across all their pickups.
* **No travel time or distance.** The pickup time is just whichever is later, the donation being ready or the volunteer's shift starting. Everything has to be in the same location to match.
* **First match, not best match.** Each donation takes the first recipient/volunteer pair that works, so neither strategy is guaranteed to be optimal.
* **Food types and locations have to match exactly**, including capitalization.
* **All the data is made up.**

## Automated Testing
RescueRoute uses Python's built-in unittest framework to verify the correctness and reliability of its scheduling functionality.
Unit tests are located in the tests directory, primarily within test_rescueroute.py.

## Running the Unit Tests
From the project's root directory, execute:
python -m unittest discover -s tests -v
This command discovers and executes the available unit tests and displays their results.

## References
* Python documentation (https://docs.python.org/3/library/) for `heapq`, `collections.deque`, `dataclasses`, `json`, `unittest`, and `tempfile`
* The CPSC 335 RescueRoute project brief
* We didn't use any outside libraries, datasets, or code.

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
   - Set up the GitHub repo and wrote the first donation and pickup-time functions (`deadline_of` and the original pickup-time check).

   - Wrote the FIFO scheduler and its explanations for assigned and unassigned donations, and hooked it up to the input data in `main.py`.

   - Wrote the greedy urgency-first scheduler using `heapq`, and made it share FIFO's matching step so the only difference is the order.

   - Added the "deferred behind" explanations so you can see which donation went ahead and why.

   - Wrote the greedy tests (ordering, FIFO vs. greedy giving different results, deferral, not changing the input, empty input).

   - Added the metrics and the FIFO vs. greedy comparison.

   - Added validation for the input values and fixed the crash on blank or broken JSON files.

   - Changed the sample data so FIFO and greedy actually give different results, and wrote most of this README.
