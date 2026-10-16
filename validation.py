# Validation of loaded donations, recipients, and volunteers
#
# load_all_data already drops entries with missing / empty fields and duplicate IDs.
# This checks that the values themselves make sense (types, ranges, known categories)
# so the schedulers never see bad data. Each invalid entry is dropped with a reason.

FOOD_TYPES = {"Prepared Meals", "Fresh Produce", "Canned Goods", "Baked Goods"}
LOCATIONS = {"North Wing", "South Wing", "Center Wing"}
DAY_MINUTES = 1440      # times are minutes from midnight, 0 to 1440


def _is_int(value):
    # bool is a subclass of int in Python, so True / False would otherwise pass
    return isinstance(value, int) and not isinstance(value, bool)


def _text(entry, field):
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        return f"{field} must be non-empty text (got {value!r})"


def _whole(entry, field, minimum):
    value = entry.get(field)
    if not _is_int(value) or value < minimum:
        return f"{field} must be a whole number of at least {minimum} (got {value!r})"


def _time(entry, field):
    value = entry.get(field)
    if not _is_int(value) or not 0 <= value <= DAY_MINUTES:
        return f"{field} must be minutes from midnight between 0 and {DAY_MINUTES} (got {value!r})"


def _one_of(entry, field, allowed):
    value = entry.get(field)
    if not isinstance(value, str) or value not in allowed:
        return f"{field} must be one of {sorted(allowed)} (got {value!r})"


def donation_errors(d):
    """Returns a list of everything wrong with one donation (empty if valid)."""
    errors = [
        _text(d, "donation_id"),
        _text(d, "donor_name"),
        _one_of(d, "food_type", FOOD_TYPES),
        _whole(d, "quantity", 1),
        _whole(d, "expire_time", 1),
        _one_of(d, "location", LOCATIONS),
        _time(d, "ready_time"),
    ]
    return [e for e in errors if e]


def recipient_errors(r):
    """Returns a list of everything wrong with one recipient (empty if valid)."""
    errors = [
        _text(r, "recipient_id"),
        _text(r, "organization_name"),
        _whole(r, "capacity", 0),
        _one_of(r, "location", LOCATIONS),
        _time(r, "closing_time"),
    ]
    foods = r.get("accepted_food_types")
    if not isinstance(foods, (list, set)) or not foods:
        errors.append(f"accepted_food_types must be a non-empty list (got {foods!r})")
    else:
        unknown = [f for f in foods if not isinstance(f, str) or f not in FOOD_TYPES]
        if unknown:
            errors.append(f"accepted_food_types has unknown types {unknown}; "
                          f"allowed: {sorted(FOOD_TYPES)}")
    return [e for e in errors if e]


def volunteer_errors(v):
    """Returns a list of everything wrong with one volunteer (empty if valid)."""
    errors = [
        _text(v, "volunteer_id"),
        _whole(v, "vehicle_capacity", 0),
        _one_of(v, "location", LOCATIONS),
        _whole(v, "maximum_pickups", 0),
        _whole(v, "pickup_counter", 0),
    ]
    shift = v.get("availability")
    if (not isinstance(shift, (list, tuple)) or len(shift) != 2
            or not all(_is_int(t) for t in shift)
            or not 0 <= shift[0] < shift[1] <= DAY_MINUTES):
        errors.append(f"availability must be [start, end] with 0 <= start < end <= "
                      f"{DAY_MINUTES} (got {shift!r})")
    return [e for e in errors if e]


def _validate(entries, kind, id_field, check):
    valid, messages = {}, []
    for key, entry in entries.items():
        errors = check(entry)
        if errors:
            messages.append(f"{kind} {entry.get(id_field, key)} rejected: {'; '.join(errors)}")
        elif kind == "Recipient":
            # Store accepted food types as a set for fast membership checks
            valid[key] = dict(entry, accepted_food_types=set(entry["accepted_food_types"]))
        else:
            valid[key] = entry
    return valid, messages


def validate_all(donations, recipients, volunteers):
    """Validates the dicts returned by load_all_data.

    Returns (donations, recipients, volunteers, messages): the valid entries of each,
    plus one human-readable message per rejected entry. The inputs are not modified.

    Time: O(D + R + V), each entry is checked once.
    """
    donations, d_msgs = _validate(donations, "Donation", "donation_id", donation_errors)
    recipients, r_msgs = _validate(recipients, "Recipient", "recipient_id", recipient_errors)
    volunteers, v_msgs = _validate(volunteers, "Volunteer", "volunteer_id", volunteer_errors)
    return donations, recipients, volunteers, d_msgs + r_msgs + v_msgs
