import json
import os

filename = "infra/chalice.tf.json"

with open(filename, "r") as file:
    d = json.load(file)

del d["terraform"]

os.remove(filename)

with open(filename, "w") as file:
    json.dump(d, file, indent=4)
