# RescueRoute

## Data Architecture & Ingestion
The system relies on JSON files (`donations.json`, `recipients.json`, `volunteers.json`) to simulate the operational environment. 
* O(1) Lookups: All entities are loaded into Python dictionaries keyed by their respective IDs (ex: "donation_id"). This ensures that the scheduling algorithms can retrieve entity data in constant time.
* Validation: "_load_json" function checks incoming data. It actively drops entries containing missing or empty fields (such as empty strings or null arrays) to prevent crashes and also checks for duplicates using a set.

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
Let D = donations, R = recipients, V = volunteers. Both strategies run in **O(D log D + D·(R + V))**: the D log D comes from sorting (FIFO) or the heap (greedy), and matching each donation scans the recipients and volunteers once.

## Automated Testing
RescueRoute uses Python's built-in unittest framework to verify the correctness and reliability of its scheduling functionality.
Unit tests are located in the tests directory, primarily within test_rescueroute.py.

## Running the Unit Tests
From the project's root directory, execute:
python -m unittest discover -s tests -v
This command discovers and executes the available unit tests and displays their results.


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
