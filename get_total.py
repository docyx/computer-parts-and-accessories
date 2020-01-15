"""
Get the total amount of items in the `data` folder.
"""
import os
import json


total = 0

for data_file in os.listdir("./data"):
    abs_path = os.path.join("./data", data_file)

    with open(abs_path, "r") as f:
        data = json.loads(f.read())

        for item in data:
            total += 1

print(total)
