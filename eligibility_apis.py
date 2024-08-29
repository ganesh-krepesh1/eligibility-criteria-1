from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, errors
from pydantic import BaseModel
import json
import configparser

app = FastAPI()

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

client = MongoClient(config['db-connection']['conn_string'])
db = client[config['db-connection']['db_name']]
data_intake = db[config['db-connection']['coll_name']]

# Added comment
@app.post("/process-data/")
async def process_data():
    try:
        # Retrieve all documents from the collection
        master_data = list(data_intake.find({}))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
    cleaned_data = []
    for data in master_data:
        if data['lastData']['qn']['display'] == 'Sex Assigned at Birth':
            cleaned_data.append(data)
        elif data['lastData']['qn']['display'] == 'Age':
            cleaned_data.append(data)

    patient_data = {}

    # Iterate over each document to collect gender and age
    for item in cleaned_data:
        patient_id = item['patient']['ref']
        
        # Initialize patient entry if not already present
        if patient_id not in patient_data:
            patient_data[patient_id] = {"gender": None, "age": None}
        
        # Check if the document contains gender information
        if 'valCodedArr' in item['lastData']['value']:
            patient_data[patient_id]['gender'] = item['lastData']['value']['valCodedArr'][0]['display']
        
        # Check if the document contains age information
        if 'valInt' in item['lastData']['value']:
            patient_data[patient_id]['age'] = item['lastData']['value']['valInt']

    # Generate the final output combining gender and age
    output = []
    for patient_id, details in patient_data.items():
        gender = details['gender']
        age = details['age']
        
        # Determine eligibility based on conditions
        if gender == "Male":
            if age < 22:
                result = "Not Eligible"
                explainability = "Patient of gender Female and age greater than 22 years are only eligible"
            else:
                result = "Not Eligible"
                explainability = "Patient with Gender Female are only eligible"
        elif gender == "Female":
            if age < 22:
                result = "Not Eligible"
                explainability = "Patient of age greater than 22 years are only eligible"
            else:
                result = "Eligible"
                explainability = None  # No explainability needed for Eligible result
        
        # Prepare the final data structure
        patient_entry = {
            "patient_id": patient_id,
            "gender": gender,
            "age": age,
            "result": result,
        }
        
        # Conditionally add the explainability field if needed
        if explainability:
            patient_entry["explainability"] = explainability
        
        # Append the final patient entry to the output list
        output.append(patient_entry)

    return output

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)