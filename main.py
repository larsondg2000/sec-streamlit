import streamlit as st
import os
import pandas as pd
import json
import requests
import tempfile
import base64
from bs4 import BeautifulSoup
from typing import Tuple
import openai
import PyPDF2
import pdfkit

# Constants
MAX_REPORTS = 12

# Streamlit app setup
st.set_page_config(page_title="SEC Report Retriever", layout="wide", page_icon=":material/assured_workload:")
st.header(":rainbow[SEC Report Retriever]", divider='rainbow')

# User input section
col1, col2 = st.columns(2)

with col1:
    ticker = st.text_input("Enter the stock ticker (e.g., MSFT):").upper()
    report_type = st.selectbox("Select the report type:", ["10-K", "10-Q", "8-K"])

with col2:
    email = st.text_input("Enter your email address:")
    max_reports = st.number_input("Maximum number of reports to retrieve:", min_value=1, max_value=MAX_REPORTS, value=5)

# Create a placeholder for outputs at the bottom
output_placeholder = st.empty()

# Add API key input and model selection
st.sidebar.title("Summarization Settings")
openai_api_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password")
model_options = ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4"]  # Ensure valid model names
selected_model = st.sidebar.selectbox("Select the summarization model:", model_options, index=0)  # Default to first model
st.sidebar.markdown("See [OpenAI's pricing](https://openai.com/pricing) for model rates and approximate costs.")

# Model prices per 1K tokens
model_prices = {
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.000075},
}

# Functions
@st.cache_data
def load_company_tickers():
    with open("company_tickers_exchange.json", "r") as f1:
        return json.load(f1)

def ticker_to_cik(ticker1: str, cik_dict1: dict) -> Tuple[str, str]:
    cik_df = pd.DataFrame(cik_dict1["data"], columns=cik_dict1["fields"])
    cik1 = cik_df[cik_df["ticker"] == ticker1].cik.values[0]
    url1 = f"https://data.sec.gov/submissions/CIK{str(cik1).zfill(10)}.json"
    return str(cik1), url1

def get_filings(url2: str, headers1: dict) -> pd.DataFrame:
    try:
        response1 = requests.get(url2, headers=headers1)
        response1.raise_for_status()
        filings_dict = json.loads(response1.text)
        return pd.DataFrame(filings_dict["filings"]["recent"])
    except requests.exceptions.RequestException as e1:
        st.error(f"Error fetching filings: {e1}")
        return pd.DataFrame()

def filter_reports(filings_df1: pd.DataFrame, report_type1: str) -> pd.DataFrame:
    return filings_df1[filings_df1.form == report_type1]

def get_exhibit_99_1_link(url3: str, headers2: dict) -> str:
    try:
        response2 = requests.get(url3, headers=headers2)
        response2.raise_for_status()
        soup = BeautifulSoup(response2.content, 'html.parser')
        base_url = url3.rsplit('/', maxsplit=1)[0] + '/'
        for link in soup.select('[href*="ex99"]'):
            return base_url + link['href']
    except requests.exceptions.RequestException as e1:
        st.error(f"Error fetching exhibit 99.1 link: {e1}")
    return ""

def create_pdf(url3: str, headers3: dict):
    try:
        st.write(f"Attempting to fetch content from URL: {url3}")
        response3 = requests.get(url3, headers=headers3)
        response3.raise_for_status()

        content_type = response3.headers.get('Content-Type', '')
        st.write(f"Content-Type of the response: {content_type}")

        if 'application/pdf' in content_type:
            # If it's a PDF, save it directly
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(response3.content)
                temp_file_path = temp_file.name
            st.write(f"Created temporary PDF file: {temp_file_path}")
            return temp_file_path, 'pdf'
        elif 'text/html' in content_type:
            st.warning("The URL returned HTML content. Attempting to convert HTML to PDF.")
            # Convert HTML to PDF using pdfkit
            try:
                # path to wkhtmltopdf
                os.environ['PATH'] += os.pathsep + 'C:\\Program Files\\wkhtmltopdf\\bin'
                config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')

                # Fetch the webpage content
                html_content = response3.text

                # Convert HTML to PDF
                # Add verbose=True for troubleshooting
                # Added options={"enable-local-file-access": None} which fixes issues with wkhtmltopdf 0.12.6
                pdf = pdfkit.from_string(html_content,
                                         False,
                                         configuration=config,
                                         options={"enable-local-file-access": None})

                # Save PDF to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(pdf)
                    temp_file_path = temp_file.name

                st.write(f"Created temporary PDF file: {temp_file_path}")
                return temp_file_path, 'pdf'
            except Exception as e2:
                st.error(f"Error converting HTML to PDF: {e2}")
                # Save HTML content to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
                    temp_file.write(response3.content)
                    temp_file_path = temp_file.name
                st.write(f"Saved HTML content to temporary file: {temp_file_path}")
                return temp_file_path, 'html'
        else:
            st.error("Unsupported content type.")
            return None, None
    except Exception as e2:
        st.error(f"Error creating PDF: {e2}")
        return None, None

def get_pdf_display_link(file_path1: str):
    try:
        with open(file_path1, "rb") as f2:
            base64_file = base64.b64encode(f2.read()).decode('utf-8')

        file_type = 'application/pdf' if file_path1.endswith('.pdf') else 'text/html'

        # File viewer
        file_display = f'<iframe src="data:{file_type};base64,{base64_file}" width="100%" height="600" type="{file_type}"></iframe>'

        # Download link
        st.markdown(
            f'<a href="data:{file_type};base64,{base64_file}" download="report{os.path.splitext(file_path1)[1]}">Download File</a>',
            unsafe_allow_html=True)

        return file_display
    except Exception as e3:
        st.error(f"Error creating display link: {e3}")
        return None

def split_text_into_chunks(text, max_chunk_size=3000):
    words = text.split()
    chunks1 = []
    for i1 in range(0, len(words), max_chunk_size):
        chunk1 = ' '.join(words[i1:i1 + max_chunk_size])
        chunks1.append(chunk1)
    return chunks1

def create_pdf_callback(report_info1):
    st.write("Create Report button clicked")
    if report_info1['report_type'] in ["10-K", "10-Q"]:
        url4 = f"https://www.sec.gov/Archives/edgar/data/{report_info1['cik']}/{report_info1['acc_number']}/{report_info1['primary_doc']}"
    elif report_info1['report_type'] == "8-K" and report_info1.get('exhibit_link'):
        url4 = report_info1['exhibit_link']
    else:
        st.warning("No PDF available for this report.")
        return

    # Display the HTML link
    st.markdown(f"**HTML Link:** [View Report]({url4})")

    # Attempt to create PDF
    file_path2, file_type = create_pdf(url4, report_info1['headers'])
    if file_path2:
        if file_type == 'pdf':
            file_display = get_pdf_display_link(file_path2)
            if file_display:
                st.markdown(file_display, unsafe_allow_html=True)
                st.success("PDF created successfully. You can view it above or download using the link.")

                # Save the file path and report info in session state
                st.session_state['file_path'] = file_path2
                st.session_state['report_info'] = report_info1
            else:
                st.error("Failed to create display link for the PDF file.")
        elif file_type == 'html':
            st.warning("Failed to convert HTML to PDF. Displaying HTML content.")
            file_display = get_pdf_display_link(file_path2)
            if file_display:
                st.markdown(file_display, unsafe_allow_html=True)
                st.success("HTML content displayed above.")
            else:
                st.error("Failed to display HTML content.")
    else:
        st.error("Failed to create the file.")

# Main app logic
if st.button("Run"):
    if not ticker or not email:
        st.warning("Please enter both ticker and email address.")
    else:
        headers = {
            "User-Agent": email,
            "Accept-Encoding": "gzip, deflate"
        }

        # Load company tickers and get CIK
        cik_dict = load_company_tickers()
        cik, url = ticker_to_cik(ticker, cik_dict)

        # Get and filter filings
        filings_df = get_filings(url, headers)
        filtered_df = filter_reports(filings_df, report_type)

        if filtered_df.empty:
            st.warning(f"No {report_type} reports found for {ticker}.")
        else:
            # Display report options
            st.subheader(f"Available {report_type} Reports for {ticker}")
            reports = filtered_df.head(max_reports)

            for idx, row in reports.iterrows():
                report_date = row['reportDate']
                acc_number = row['accessionNumber'].replace('-', '')
                primary_doc = row['primaryDocument']

                report_info = {
                    'report_date': report_date,
                    'acc_number': acc_number,
                    'primary_doc': primary_doc,
                    'cik': cik,
                    'headers': headers,
                    'report_type': report_type
                }

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"{report_type} - {report_date}")

                with col2:
                    if report_type == "8-K":
                        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_number}/{primary_doc}"
                        exhibit_link = get_exhibit_99_1_link(url, headers)
                        if exhibit_link:
                            st.write("Exhibit 99.1 available")
                        else:
                            st.write("No Exhibit 99.1")
                        report_info['exhibit_link'] = exhibit_link

                with col3:
                    button_key = f"create_pdf_{idx}"
                    st.button("Create Report", key=button_key, on_click=create_pdf_callback, args=(report_info,))

# Check if a report has been generated and display the Summarize button
if 'file_path' in st.session_state and 'report_info' in st.session_state:
    st.markdown("---")
    st.subheader("Summarize Report")

    if openai_api_key:
        if st.button("Summarize Report"):
            file_path = st.session_state['file_path']
            report_info = st.session_state['report_info']

            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                full_text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    full_text += page.extract_text()
            # Now split the text into chunks
            if selected_model == "gpt-3.5-turbo":
                chunk_size = 3000  # Approximate words
            elif selected_model == "gpt-4" or selected_model == "gpt-4o-mini":
                chunk_size = 6000
            else:
                chunk_size = 3000

            chunks = split_text_into_chunks(full_text, max_chunk_size=chunk_size)
            openai.api_key = openai_api_key
            summaries = []
            total_prompt_tokens = 0
            total_completion_tokens = 0
            for i, chunk in enumerate(chunks):
                st.write(f"Summarizing chunk {i+1}/{len(chunks)}...")
                try:
                    response = openai.ChatCompletion.create(
                        model=selected_model,
                        messages=[
                            {"role": "system",
                             "content": "You are an AI assistant specialized in summarizing SEC 10-K, 10-Q, and 8-K "
                                        "(exhibit 99.1) reports. Your primary function is to extract and present key "
                                        "financial information, company updates, and potential risk factors from these "
                                        "documents. please format the output to account for special characters and fonts. "},
                            {"role": "user",
                             "content": f"Please summarize the following text with appropriate currency symbols, "
                                        f"percentages, and other special characters.  "
                                        f"The output should be easy to read using the same font and style:\n\n{chunk}. "}
                        ]
                    )
                    summary = response['choices'][0]['message']['content']
                    summaries.append(summary)
                    usage = response['usage']
                    total_prompt_tokens += usage.get('prompt_tokens', 0)
                    total_completion_tokens += usage.get('completion_tokens', 0)
                except Exception as e:
                    st.error(f"An error occurred during summarization: {e}")

            # Now combine the summaries
            combined_summary = "\n".join(summaries)
            # Optionally, generate a final summary
            st.write("Generating final summary...")
            try:
                response = openai.ChatCompletion.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content":
                            "You are a helpful assistant that summarizes SEC reports."},
                        {"role": "user", "content": f"Please provide a concise summary of the following:\n\n{combined_summary}"}
                    ]
                )
                final_summary = response['choices'][0]['message']['content']
                usage = response['usage']
                total_prompt_tokens += usage.get('prompt_tokens', 0)
                total_completion_tokens += usage.get('completion_tokens', 0)
                st.subheader("Summary:")
                st.write(final_summary)
            except Exception as e:
                st.error(f"An error occurred during final summarization: {e}")

            # Calculate approximate cost
            total_tokens = total_prompt_tokens + total_completion_tokens
            prompt_cost = (total_prompt_tokens / 1000) * model_prices[selected_model]["prompt"]
            completion_cost = (total_completion_tokens / 1000) * model_prices[selected_model]["completion"]
            total_cost = prompt_cost + completion_cost

            st.write(f"**Total tokens used:** {total_tokens}")
            st.write(f"**Approximate cost:** ${total_cost:.4f}")

    else:
        st.info("Enter your OpenAI API key in the sidebar to enable summarization.")

st.markdown("---")
st.markdown("""
### Terms
* **SEC Form 10-K**: an annual report that public companies must file with the Securities and Exchange Commission (SEC) 
to provide a comprehensive summary of their financial performance, including audited financial statements, management 
discussion and analysis, and other disclosures.
* **SEC Form 10-Q**:  a quarterly report that public companies must file with the SEC to provide a summary of their financial 
performance for the past three months, including unaudited financial statements, management discussion and analysis, 
and other disclosures.
* **SEC Form 8-K**:  a report that companies must file with the Securities and Exchange Commission (SEC) to announce major 
events that shareholders should know about.
* **SEC Exhibit 99.1**:  a document that is filed with the Securities and Exchange Commission (SEC) by companies to provide 
additional information about a particular event or transaction.

### Links
- SEC Main Page:  https://www.sec.gov/
- SEC Developer Resources:  https://www.sec.gov/developer
- Open AI API key: https://platform.openai.com/api-keys
- Open AI model information: https://platform.openai.com/docs/models
- Open AI model pricing: https://openai.com/pricing
"""
)

st.markdown("---")
st.write("Note: This app uses the SEC's EDGAR database. Please ensure you comply with their terms of service.")
