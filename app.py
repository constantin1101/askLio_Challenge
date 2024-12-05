import json
import pdfplumber
import re
import csv
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import filedialog
import openai
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from werkzeug.utils import secure_filename


# Flask app initialization
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.secret_key = 'supersecretkey'

CSV_FILE = "procurement_db.csv"

load_dotenv()  # Load environment variables from .env file
openai_key = os.getenv('OPENAI_API_KEY')

commodity_dict = {
    "001": ["General Services", "Accommodation Rentals"],
    "002": ["General Services", "Membership Fees"],
    "003": ["General Services", "Workplace Safety"],
    "004": ["General Services", "Consulting"],
    "005": ["General Services", "Financial Services"],
    "006": ["General Services", "Fleet Management"],
    "007": ["General Services", "Recruitment Services"],
    "008": ["General Services", "Professional Development"],
    "009": ["General Services", "Miscellaneous Services"],
    "010": ["General Services", "Insurance"],
    "011": ["Facility Management", "Electrical Engineering"],
    "012": ["Facility Management", "Facility Management Services"],
    "013": ["Facility Management", "Security"],
    "014": ["Facility Management", "Renovations"],
    "015": ["Facility Management", "Office Equipment"],
    "016": ["Facility Management", "Energy Management"],
    "017": ["Facility Management", "Maintenance"],
    "018": ["Facility Management", "Cafeteria and Kitchenettes"],
    "019": ["Facility Management", "Cleaning"],
    "020": ["Publishing Production", "Audio and Visual Production"],
    "021": ["Publishing Production", "Books/Videos/CDs"],
    "022": ["Publishing Production", "Printing Costs"],
    "023": ["Publishing Production", "Software Development for Publishing"],
    "024": ["Publishing Production", "Material Costs"],
    "025": ["Publishing Production", "Shipping for Production"],
    "026": ["Publishing Production", "Digital Product Development"],
    "027": ["Publishing Production", "Pre-production"],
    "028": ["Publishing Production", "Post-production Costs"],
    "029": ["Information Technology", "Hardware"],
    "030": ["Information Technology", "IT Services"],
    "031": ["Information Technology", "Software"],
    "032": ["Logistics", "Courier, Express, and Postal Services"],
    "033": ["Logistics", "Warehousing and Material Handling"],
    "034": ["Logistics", "Transportation Logistics"],
    "035": ["Logistics", "Delivery Services"],
    "036": ["Marketing & Advertising", "Advertising"],
    "037": ["Marketing & Advertising", "Outdoor Advertising"],
    "038": ["Marketing & Advertising", "Marketing Agencies"],
    "039": ["Marketing & Advertising", "Direct Mail"],
    "040": ["Marketing & Advertising", "Customer Communication"],
    "041": ["Marketing & Advertising", "Online Marketing"],
    "042": ["Marketing & Advertising", "Events"],
    "043": ["Marketing & Advertising", "Promotional Materials"],
    "044": ["Production", "Warehouse and Operational Equipment"],
    "045": ["Production", "Production Machinery"],
    "046": ["Production", "Spare Parts"],
    "047": ["Production", "Internal Transportation"],
    "048": ["Production", "Production Materials"],
    "049": ["Production", "Consumables"],
    "050": ["Production", "Maintenance and Repairs"]
}

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(file_path):
    try:
        # Open the PDF file
        with pdfplumber.open(file_path) as pdf:
            text = " ".join([page.extract_text() for page in pdf.pages])
        return text
    except Exception as e:
        print(f"Error extracting data from PDF: {e}")
        return None
    
def extract_information_from_text(text, key):
    # import system_message.txt as a string
    with open('prompts/extract_information.txt', 'r') as file:
        system_message = file.read()

    client = openai.OpenAI(api_key=key)

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ]
        )
        # Instantly add the output as a new column entry for the corresponding row
        response = completion.choices[0].message.content
        return response 

    except openai.error.OpenAIError as e:
        print(f"An exception occurred: {e}")
        return None

def check_procurement_request(response):
    # Parse the JSON strings
    response = json.loads(response)

    if response['requestor_name'] and response['title'] and response['vendor_name'] and response['vat_id'] != "" and response['order_lines'] != [] and response['total_cost'] != 0.0:
        return True
    else:
        return False
    
def identify_commodity(text, commodity_dict, key):
    system_message = system_message = (
    f"Using the list of possible commodities {commodity_dict}, "
    f"please identify the commodity in the text: {text}. "
    "Return commodity as a JSON object. "
    "**Output Format**: Return a JSON object structured exactly as shown below. "
    "Include no additional text or formatting. "
    '{"ID": "string", "Category": "string", "Commodity Group": "string"}'
)

    client = openai.OpenAI(api_key=key)

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ]
        )
        # Instantly add the output as a new column entry for the corresponding row
        response = completion.choices[0].message.content
        
        return response

    except openai.error.OpenAIError as e:
        print(f"An exception occurred: {e}")
        return None

def save_to_csv(data, commodity):
    csv_file="procurement_db.csv"
    # Parse the JSON strings
    data = json.loads(data)
    print(data)
    commodity = json.loads(commodity)

    # Combine order lines into a single column
    order_lines_combined = "; ".join(
        [
            f"{line['unit_price']} - {line['amount']} {line['unit']}"
            for line in data["order_lines"]
        ]
    )

    # Prepare the row for CSV
    row = {
        "Requestor Name": data["requestor_name"],
        "Title": data["title"],
        "Vendor Name": data["vendor_name"],
        "VAT ID": data["vat_id"],
        "Commodity ID": commodity["ID"],
        "Commodity Category": commodity["Category"],
        "Commodity Group": commodity["Commodity Group"],
        "Order Lines (Unit Price, Amount, Unit)": order_lines_combined,  # Combined order lines in a single column
        "Total Cost": data["total_cost"],
        "Department": data["department"],
        "Status": "Open",
    }

    # Define CSV file headers
    headers = [
        "Requestor Name", "Title", "Vendor Name", "VAT ID", "Commodity ID",
        "Commodity Category", "Commodity Group", "Order Lines (Unit Price, Amount, Unit)", "Total Cost",
        "Department", "Status"
    ]

    # Write or append to CSV
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        if not file_exists:
            # Write the header if the file does not exist
            writer.writeheader()
        # Append the row
        writer.writerow(row)

    print(f"Data has been saved to {csv_file}.")

# Utility function to read CSV data
def read_csv(file_path):
    if not os.path.isfile(file_path):
        return []
    
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [row for row in reader]

# Route for the main page
@app.route('/')
def index():
    # Read the contents of the CSV file
    csv_data = read_csv(CSV_FILE)
    return render_template('index.html', csv_data=csv_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the request has a file
    if 'file' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    # Check if a file is selected
    if file.filename == '':
        flash('No file selected. Please choose a file.')
        return redirect(url_for('index'))
    
    # Validate file type
    if not allowed_file(file.filename):
        flash('Invalid file type. Only PDF files are supported.')
        return redirect(url_for('index'))
    
    # Secure and save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Extract text from PDF
    extracted_text = extract_text_from_pdf(file_path)
    if not extracted_text:
        flash('No data extracted. Please check the PDF format and content.')
        return redirect(url_for('index'))
    
    flash('Data extracted successfully.')
    
    # Extract structured information from text
    try:
        extracted_data = extract_information_from_text(extracted_text, openai_key)
    except Exception as e:
        flash(f"Error extracting structured information: {e}")
        return redirect(url_for('index'))

    # Check if the response contains the required fields
    if check_procurement_request(extracted_data) == False:
        flash('The extracted data does not contain all the required fields. Please try again.')
        return redirect(url_for('index'))
    
    # Identify the commodity
    try:
        commodity = identify_commodity(extracted_text, commodity_dict, openai_key)
    except Exception as e:
        flash(f"Error identifying commodity: {e}")
        return redirect(url_for('index'))
    
    # Save to CSV
    try:
        save_to_csv(extracted_data, commodity)
        flash('Data saved to CSV successfully.')
    except Exception as e:
        flash(f"Error saving data to CSV: {e}")
        return redirect(url_for('index'))
    
    return render_template('result.html', data=extracted_data, commodity=commodity)

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    row_index = data.get('rowIndex')
    new_status = data.get('status')

    # Read the CSV
    csv_file = "procurement_db.csv"
    rows = read_csv(csv_file)

    if 0 <= row_index < len(rows):
        # Update the status
        rows[row_index]["Status"] = new_status

        # Write the updated rows back to the CSV
        headers = rows[0].keys()
        with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return jsonify({"message": "Status updated successfully"}), 200

    return jsonify({"error": "Invalid row index"}), 400

# Run the app
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
