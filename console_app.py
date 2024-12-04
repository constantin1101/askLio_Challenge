import json
import pdfplumber
import re
import csv
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import filedialog
import openai


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

    # Prepare data for CSV
    csv_data = []
    for order_line in data["order_lines"]:
        row = {
            "Requestor Name": data["requestor_name"],
            "Title": data["title"],
            "Vendor Name": data["vendor_name"],
            "VAT ID": data["vat_id"],
            "Commodity ID": commodity["ID"],
            "Commodity Category": commodity["Category"],
            "Commodity Group": commodity["Commodity Group"],
            "Position Description": order_line["position_description"],
            "Unit Price": order_line["unit_price"],
            "Amount": order_line["amount"],
            "Unit": order_line["unit"],
            "Total Cost": data["total_cost"],
            "Department": data["department"],
            "Status": "Open"
        }
        csv_data.append(row)

    # Define CSV file headers
    headers = [
        "Requestor Name", "Title", "Vendor Name", "VAT ID", "Commodity ID",
        "Commodity Category", "Commodity Group", "Position Description",
        "Unit Price", "Amount", "Unit", "Total Cost", "Department", "Status"
    ]

    # Write or append to CSV
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        if not file_exists:
            # Write the header if the file does not exist
            writer.writeheader()
        # Append the rows
        writer.writerows(csv_data)

    print(f"Data has been saved to {csv_file}.")

def main():
    load_dotenv()  # Load environment variables from .env file
    openai_key = os.getenv('OPENAI_API_KEY')
    print(openai_key)

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

    print("Welcome to the Procurement Request Processor!")
    # Open a file dialog to select the PDF file
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(
        title="Select Vendor Offer PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )
    
    # Check if the user selected a file
    if not file_path:
        print("No file selected. Exiting.")
        return
    
    # Validate the selected file
    if not os.path.isfile(file_path) or not file_path.endswith(".pdf"):
        print("Invalid file. Please ensure the file exists and is a PDF.")
        return
    
    # Extract information from the PDF
    extracted_data = extract_text_from_pdf(file_path)

    if extracted_data:
        print("Data extracted successfully.")
    else:
        print("No data extracted. Please check the PDF format and content.")

    # Extract information from the text
    if extracted_data:
        extracted_data = extract_information_from_text(extracted_data, openai_key)
    else:
        print("No data extracted. Please check the PDF format and content.")
        return
    
    commodity = identify_commodity(extracted_data, commodity_dict, openai_key)

    # Save the extracted data to a CSV file
    if extracted_data and commodity:
        save_to_csv(extracted_data, commodity)
    else:
        print("No data extracted. Please check the PDF format and content.")
    

if __name__ == "__main__":
    main()
