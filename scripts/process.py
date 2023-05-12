import json
import os

from pandas import read_csv


def convert_csv_to_jsonl(data):
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


def merge_all_jsonl():
    """
    go over all jsonl files in
    addd all data to a single jsonl file
    """
    jsonl_files = os.listdir("/Users/megham/MedicalGPT/fine_tuning_data")
    all_jsonl = []
    for file in jsonl_files:
        with open(f"/Users/megham/MedicalGPT/fine_tuning_data/{file}") as f:
            jsonl = f.readlines()
            all_jsonl.extend(jsonl)
    with open("/Users/megham/MedicalGPT/fine_tuning_data/data.jsonl", "w") as f:
        f.writelines(all_jsonl)


def process_data_jsonl():
    with open("/Users/megham/MedicalGPT/fine_tuning_data/data.jsonl") as f:
        jsonl = f.readlines()
        processed_jsonl = []
        for line in jsonl:
            line = json.loads(line)
            prompt = line["prompt"]
            completion = line["completion"]
            processed_jsonl.append(
                {
                    "prompt": (
                        f"Question: Is following sentence indicating {completion}?\nSentence: {prompt}\nAnswer:Yes/No"
                    )
                    .lower()
                    .strip(),
                    "completion": "yes",
                }
            )
    with open("/Users/megham/MedicalGPT/fine_tuning_data/processed.jsonl", "w") as f:
        for item in processed_jsonl:
            f.write("%s\n" % json.dumps(item))
