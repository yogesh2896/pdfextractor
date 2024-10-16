import os
import requests
import streamlit as st
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PIL import Image
import urllib.request

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
    Location Ownership:
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

# Streamlit UI setup
st.set_page_config(page_title="PDF Data Extractor", page_icon=":page_facing_up:", layout="wide")

# Custom CSS for styling
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: #f8f9fa;
        color: #333333;
    }}
    .main-content {{
        background-color: #ffffff;
        color: #333333;
        padding: 20px;
        border-radius: 10px;
        border: 3px solid #FF6F61;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
        animation: fadeIn 1.5s ease-in-out;
    }}
    .stButton>button {{
        background-color: #FF6F61;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 10px;
        transition: all 0.3s;
    }}
    .stButton>button:hover {{
        background-color: #88B04B;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
        transform: scale(1.05);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Display company logo in the top right corner
logo = fetch_logo(company_logo_url)
col1, col2 = st.columns([8, 2])
with col1:
    st.title("PDF Data Extractor using Azure OpenAI")
with col2:
    st.image(logo, use_column_width=True)

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
                st.text_area("Extracted Data:", value=extracted_fields, height=300)
            else:
                st.warning("No data extracted.")
st.markdown('</div>', unsafe_allow_html=True)
