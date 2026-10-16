# RescueRoute: FIFO vs. Greedy Comparison Report

CPSC 335 Group Project: Kihyun Won, Elias Zoreikat, Ethan Akahoshi

*This is a school project using made-up data. It is not meant for real food pickups or emergencies.*

## 1. The Two Strategies

We ran both strategies on the same sample data (10 donations, 10 recipients, 10 volunteers). They both use the same matching step: for each donation, go through the recipients and volunteers and take the first pair that passes `check_compatibility` (the recipient accepts the food type, everyone is in the same location, the volunteer hasn't hit their pickup limit, and the times work out) and `check_capacity` (the recipient and the volunteer's car both have enough room left). The only difference is the **order** the donations get handled in, so any difference in the results comes from the ordering.

**FIFO:** handles donations in the order they arrive (earliest `ready_time` first) using a deque.

**Greedy urgency-first:** handles donations in this order using a heap:
1. earliest expiration deadline (`ready_time + expire_time`) first
2. if tied, the bigger quantity first
3. if still tied, the earlier `ready_time`, then whichever came first in the list

Both are O(D log D + D·R·V), where D, R, and V are the number of donations, recipients, and volunteers.

## 2. Results

This is what `python main.py` gives on our sample data:

| Metric | FIFO | Greedy | Difference |
|---|---|---|---|
| Donations received | 10 | 10 | 0 |
| Donations assigned | 7 | 7 | 0 |
| Donations unassigned | 3 | 3 | 0 |
| Food quantity rescued (units) | 185 | 190 | +5 |
| Food quantity at risk (units) | 100 | 95 | -5 |
| Urgent rescue rate | 66.7% | 100.0% | +33.3 |
| Recipient capacity utilization | 30.8% | 31.7% | +0.8 |
| Volunteer capacity utilization | 43.0% | 44.2% | +1.2 |

We count the earliest-expiring 25% of donations as "urgent", which for our data is D007, D001, and D002. Utilization is the food rescued divided by the total capacity of all recipients (600 units) or all volunteer cars (430 units).

## 3. What Changed and Why

8 out of the 10 donations end up the same either way. The whole difference comes from two donations fighting over one recipient:

| Donation | Food | Quantity | Ready | Expires |
|---|---|---|---|---|
| D004 | Fresh Produce, North Wing | 30 | 11:00 AM | 1:00 AM the next day |
| D007 | Fresh Produce, North Wing | 35 | 1:00 PM | 3:00 PM |

The only North Wing recipient that takes produce is Senior Citizens Center, and it only has room for 45 units. So it can take one of them, but not both.

- **FIFO** does D004 first because it was ready two hours earlier. That uses up 30 units and leaves 15, so D007 gets rejected. The program says: *"no recipient in North Wing that accepts Fresh Produce had 35 units of remaining capacity."* So the most urgent donation in the whole data set doesn't get picked up.
- **Greedy** does D007 first because it expires the soonest (3:00 PM). So D007 gets rescued and D004 gets rejected instead. The program says: *"It was deferred behind D007 under the urgency-first rule because D007 expires at 3:00 PM, before D004 expires at 1:00 AM the next day."*

That's why greedy gets a 100% urgent rescue rate (vs. 66.7%) and saves 5 more units (D007 is 5 units bigger than D004), even though both strategies assign 7 donations. The other two unassigned donations fail no matter which order you use: D009 needs 50 units and no Center Wing volunteer has a big enough car, and D010 doesn't have a volunteer on shift in time.

## 4. Trade-offs and Fairness

**What greedy optimizes:** at each step, the food that's closest to going bad gets first pick of whatever capacity is left. We think this makes sense because food that lasts a long time can usually be picked up later or go somewhere else, but urgent food is just wasted if nobody takes it in time.

**Fairness and starvation:** greedy isn't fair to donations that last a long time. D004 showed up first and would have been rescued with FIFO, but it lost its only possible recipient to a donation that came later. If urgent donations keep showing up, a long-lasting donation could keep getting pushed back until there's no room left anywhere, which is starvation. Two ways we could fix this (that we didn't implement) are saving some capacity for older donations, or slowly raising a donation's priority the longer it waits (aging).

**When greedy could do worse than FIFO:** greedy doesn't look ahead. Each donation still takes the *first* recipient that works, so an urgent donation might take a spot that a later donation really needed. For example, say one recipient takes both produce and canned goods and is listed before another recipient that only takes produce. An urgent produce donation could take the first one and leave a canned goods donation with nowhere to go, even though both could have fit. So neither strategy is guaranteed to be optimal.

**Assumptions that affect the results:** both strategies plan the whole day at once, so greedy can push back a donation that's ready at 8:00 AM behind one that isn't ready until 1:00 PM (the 8:00 AM pickup time doesn't change though). We also treat vehicle capacity as a total for the whole day instead of per trip, and we don't model travel time.

## 5. Conclusion

For our sample data, greedy is the better strategy if the main goal is not wasting the most perishable food. It rescued every urgent donation (100% vs. 66.7%) and 5 more units of food overall, while assigning the same number of donations. The downside is fairness: D004 showed up earlier but got rejected so a more urgent donation could be saved, and the program explains exactly why. When there's plenty of capacity, both strategies give the same results, since the order only matters when donations are competing for the same space. If we were picking one for a real food rescue operation, we'd go with greedy but add something like aging or reserved capacity so long-lasting donations don't get starved.
