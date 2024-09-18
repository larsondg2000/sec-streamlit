import streamlit as st
import os
import pandas as pd
import json
import requests
import tempfile
import base64
from bs4 import BeautifulSoup
from typing import List, Tuple
import pdfkit
import shutil

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

# Functions
@st.cache_data
def load_company_tickers():
    with open("company_tickers_exchange.json", "r") as f:
        return json.load(f)


def ticker_to_cik(ticker: str, cik_dict: dict) -> Tuple[str, str]:
    cik_df = pd.DataFrame(cik_dict["data"], columns=cik_dict["fields"])
    cik = cik_df[cik_df["ticker"] == ticker].cik.values[0]
    url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
    return str(cik), url


def get_filings(url: str, headers: dict) -> pd.DataFrame:
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        filings_dict = json.loads(response.text)
        return pd.DataFrame(filings_dict["filings"]["recent"])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching filings: {e}")
        return pd.DataFrame()


def filter_reports(filings_df: pd.DataFrame, report_type: str) -> pd.DataFrame:
    return filings_df[filings_df.form == report_type]


def get_exhibit_99_1_link(url: str, headers: dict) -> str:
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        base_url = url.rsplit('/', maxsplit=1)[0] + '/'
        for link in soup.select('[href*="ex99"]'):
            return base_url + link['href']
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching exhibit 99.1 link: {e}")
    return ""


def create_pdf(url: str, headers: dict):
    try:
        st.write(f"Attempting to fetch content from URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        st.write(f"Content-Type of the response: {content_type}")

        if 'application/pdf' in content_type:
            # If it's a PDF, save it directly
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            st.write(f"Created temporary PDF file: {temp_file_path}")
            return temp_file_path, 'pdf'
        elif 'text/html' in content_type:
            st.warning("The URL returned HTML content. Attempting to convert HTML to PDF.")
            # Convert HTML to PDF using pdfkit
            try:
                # path to wkhtmltopdf
                path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
                config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

                # Fetch the webpage content
                html_content = response.text

                # Convert HTML to PDF
                pdf = pdfkit.from_string(html_content, False, configuration=config)

                # Save PDF to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    temp_file.write(pdf)
                    temp_file_path = temp_file.name

                st.write(f"Created temporary PDF file: {temp_file_path}")
                return temp_file_path, 'pdf'
            except Exception as e:
                st.error(f"Error converting HTML to PDF: {e}")
                # Save HTML content to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                st.write(f"Saved HTML content to temporary file: {temp_file_path}")
                return temp_file_path, 'html'
        else:
            st.error("Unsupported content type.")
            return None, None
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None, None


def get_pdf_display_link(file_path: str):
    try:
        with open(file_path, "rb") as f:
            base64_file = base64.b64encode(f.read()).decode('utf-8')

        file_type = 'application/pdf' if file_path.endswith('.pdf') else 'text/html'

        # File viewer
        file_display = f'<iframe src="data:{file_type};base64,{base64_file}" width="100%" height="600" type="{file_type}"></iframe>'

        # Download link
        st.markdown(
            f'<a href="data:{file_type};base64,{base64_file}" download="report{os.path.splitext(file_path)[1]}">Download File</a>',
            unsafe_allow_html=True)

        return file_display
    except Exception as e:
        st.error(f"Error creating display link: {e}")
        return None


def create_pdf_callback(report_info):

    st.write("Create PDF button clicked")
    if report_info['report_type'] in ["10-K", "10-Q"]:
        url = f"https://www.sec.gov/Archives/edgar/data/{report_info['cik']}/{report_info['acc_number']}/{report_info['primary_doc']}"
    elif report_info['report_type'] == "8-K" and report_info.get('exhibit_link'):
        url = report_info['exhibit_link']
    else:
        st.warning("No PDF available for this report.")
        return

    # Display the HTML link
    st.markdown(f"**HTML Link:** [View Report]({url})")

    # Attempt to create PDF
    file_path, file_type = create_pdf(url, report_info['headers'])
    if file_path:
        if file_type == 'pdf':
            file_display = get_pdf_display_link(file_path)
            if file_display:
                st.markdown(file_display, unsafe_allow_html=True)
                st.success("PDF created successfully. You can view it above or download using the link.")
            else:
                st.error("Failed to create display link for the PDF file.")
        elif file_type == 'html':
            st.warning("Failed to convert HTML to PDF. Displaying HTML content.")
            file_display = get_pdf_display_link(file_path)
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

    st.markdown("---")
    st.write("Note: This app uses the SEC's EDGAR database. Please ensure you comply with their terms of service.")
