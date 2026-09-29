from data import Donations, Recipients, Volunteers
from Algo import check_time

good = {"ready_time": 380, "expire_time": 720}
bad  = {"ready_time": 400, "expire_time": 30}
vol  = {"availability": [480, 1020]}


rec = {"organization_name": "Helping Hands", "closing_time": 1020}
vol = {"availability": [480, 1020]}

print(check_time({"ready_time": 380,  "expire_time": 720}, rec, vol))   # A
print(check_time({"ready_time": 400,  "expire_time": 30},  rec, vol))   # B
print(check_time({"ready_time": 1080, "expire_time": 120}, rec, vol))   # C
print(check_time({"ready_time": 900,  "expire_time": 300},
                 {"organization_name": "Shelter", "closing_time": 850}, vol))  # D
