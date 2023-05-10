import json

from pandas import read_csv

# Read the data from the CSV file, with first row as column names
data = read_csv("data.csv", header=0)

# iterate column wise
for col in data.columns:
    # get unique values of the column
    unique_values = data[col].unique()
    jsonl = []
    for val in unique_values:
        # create a json object
        json_obj = {
            "prompt": str(val).lower().strip(),
            "completion": str(col).lower().strip(),
        }
        jsonl.append(json_obj)
    # write the json object to a file
    with open(
        f"jsons/{str(col).lower().strip().replace(' ', '_')}.jsonl",
        "a",
    ) as f:
        for item in jsonl:
            f.write("%s\n" % json.dumps(item))
