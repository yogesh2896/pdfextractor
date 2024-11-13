import os
import requests
import streamlit as st
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PIL import Image
import urllib.request
import json

# Azure configuration
form_recognizer_endpoint = "https://docintelligenceocrtest.cognitiveservices.azure.com/"
form_recognizer_key = "c886a499d57d482b8d8a2c98ba6e9820"
openai_api_key = "3db3696541524407bdbbba4879d9d24e"
openai_endpoint = "https://azureocrllmtesting.openai.azure.com/openai/deployments/TESTOCRLLMDeployGPT35/chat/completions?api-version=2024-08-01-preview"

# URL for the company logo
company_logo_url = "https://enoahisolution.com/wp-content/themes/enoah-new/images/newimages/enoah-logo-fixed.png"  # Replace with actual logo URL

# Function to fetch the logo
def fetch_logo(logo_url):
    with urllib.request.urlopen(logo_url) as response:
        logo_image = Image.open(response)
    return logo_image

# Function to analyze document using Azure Form Recognizer
def analyze_document(pdf_file_path):
    client = DocumentAnalysisClient(endpoint=form_recognizer_endpoint, credential=AzureKeyCredential(form_recognizer_key))
    with open(pdf_file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", document=f)
    result = poller.result()
    extracted_text = ""
    for page in result.pages:
        for line in page.lines:
            extracted_text += line.content + "\n"
    return extracted_text.strip()

# Function to send extracted text to Azure OpenAI for field mapping
def send_to_openai(extracted_text):
    prompt = f"""
    Extract the following fields from the provided PDF text. If the name is present as a single name, return it as it is. If a first and last name are present, return them separately as 'First Name' and 'Last Name'.
    Return the results in the following format:
    Business Legal Name:
    Federal ID (or) Federal Tax ID (or) Federal Tax Identification Number:
    Name:
    (or)
    First Name:
    Last Name:
    Date of Birth:
    SSN:
    Mobile:
    Email Address:
    Loan Amount:
    Credit Score:
    Location:
    Ownership:
    
    Here is the extracted text:
    {extracted_text}
    """
    headers = {
        "api-key": openai_api_key,
        "Content-Type": "application/json"
    }
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400
    }
    response = requests.post(openai_endpoint, headers=headers, json=data)
    if response.status_code == 200:
        response_json = response.json()
        return response_json['choices'][0]['message']['content']
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# Function to convert extracted text into a dictionary with improved handling for empty values
def parse_extracted_text_to_dict(extracted_text):
    lines = extracted_text.split("\n")
    extracted_dict = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            # Strip whitespace and handle cases where value might be missing
            extracted_dict[key.strip()] = value.strip() if value.strip() else ""
        else:
            # Handle cases where the key might have been split across lines
            if line.strip() and key in extracted_dict and not extracted_dict[key]:
                extracted_dict[key] = line.strip()
    return extracted_dict

# Streamlit UI setup
st.set_page_config(page_title="PDF Data Extractor", page_icon=":page_facing_up:", layout="wide")

# Custom CSS for styling
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
        color: #333333;
    }
    .main-content {
        background-color: #ffffff;
        color: #333333;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
        animation: fadeIn 1.5s ease-in-out;
    }
    .header-box {
        background-color: #FF6F61;
        color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #FF6F61;
        color: white;
        border: none;
        padding: 8px 15px;  /* Reduced size */
        border-radius: 10px;
        transition: all 0.3s;
        font-size: 14px; /* Reduced font size */
    }
    .stButton>button:hover {
        background-color: #88B04B;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
        transform: scale(1.05);
    }
    .stDownloadButton > button {
        background-color: #000000;
        color: white;
        border: none;
        padding: 8px 15px;  /* Reduced size */
        border-radius: 10px;
        transition: all 0.3s;
        font-size: 14px; /* Reduced font size */
    }
    .stDownloadButton > button:hover {
        background-color: #444444;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
        transform: scale(1.05);
    }
    .logo {
        width: 80px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display company logo in the left corner
logo = fetch_logo(company_logo_url)
st.image(logo, width=80, caption="")

# Title under the logo
st.markdown('<div class="header-box">OCR Smart Reader</div>', unsafe_allow_html=True)

# Main container
st.markdown('<div class="main-content">', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file is not None:
    pdf_file_path = uploaded_file.name
    with open(pdf_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button("Extract"):
        with st.spinner("Extracting data..."):
            # Step 1: Analyze the document
            extracted_content = analyze_document(pdf_file_path)

            # Step 2: Send to Azure OpenAI for field extraction
            extracted_fields = send_to_openai(extracted_content)

            if extracted_fields:
                st.success("Extraction successful!")

                # Store extracted data and file name in session state
                st.session_state.extracted_fields = extracted_fields
                st.session_state.pdf_file_name = pdf_file_path

# Display extracted fields and PDF name if present in session state
if "extracted_fields" in st.session_state and st.session_state.extracted_fields:
    # Display the PDF file name as a title
    st.markdown(f"### {st.session_state.pdf_file_name}")

    # Display extracted data in the text area
    st.text_area("Extracted Data:", value=st.session_state.extracted_fields, height=300)

    # Step 3: Parse extracted text into a dictionary
    extracted_fields_dict = parse_extracted_text_to_dict(st.session_state.extracted_fields)

    # Wrap the extracted data in a dictionary with the PDF file name as the key
    extracted_data = {st.session_state.pdf_file_name: extracted_fields_dict}

    # Convert the dictionary to JSON format
    extracted_fields_json = json.dumps(extracted_data, indent=4)

    # Add a Download JSON button with black background and white font
    st.download_button(
        label="Download JSON",
        data=extracted_fields_json,
        file_name=f"{st.session_state.pdf_file_name.split('.')[0]}_extracted_data.json",  # PDF name in the JSON file name
        mime="application/json"
    )

# Clear session state if a new file is uploaded
if uploaded_file and "extracted_fields" in st.session_state and st.session_state.pdf_file_name != uploaded_file.name:
    st.session_state.extracted_fields = None
    st.session_state.pdf_file_name = None

st.markdown('</div>', unsafe_allow_html=True)
