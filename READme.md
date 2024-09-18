# 10-K, 10-Q, and 8-K Reports from SEC Database
#### _Includes Exhibit 99.1 Reports_
![alt-text](ws2.jpeg "Wall Street") 

![alt-text](msft8k.png "8-K Press Release")

- SEC Main Page: https://www.sec.gov/
- SEC Developer Resources: https://www.sec.gov/developer

## Overview
The program creates 10-K, 10-Q, or 8-K exhibit 99.1 reports using data from the SEC database (EDGAR). The user 
inputs a stock ticker, selects the report type, your email address (to access EDGAR), and the number of reports desired.  

For the reports, the query results will be displayed (maximum of 12) and the user can select "create report".  The
report will create a link to the report, a downloadable pdf link, and display the report in a window. 

## Terms
* SEC Form 10-K: an annual report that public companies must file with the Securities and Exchange Commission (SEC) 
to provide a comprehensive summary of their financial performance, including audited financial statements, management 
discussion and analysis, and other disclosures.
* SEC Form 10-Q: a quarterly report that public companies must file with the SEC to provide a summary of their financial 
performance for the past three months, including unaudited financial statements, management discussion and analysis, 
and other disclosures.
* SEC Form 8-K: a report that companies must file with the Securities and Exchange Commission (SEC) to announce major 
events that shareholders should know about.
* SEC Exhibit 99.1: a document that is filed with the Securities and Exchange Commission (SEC) by companies to provide 
additional information about a particular event or transaction.
* CIK: Central Index Key-EDGAR uses this number to identify a Company 
* Ticker: ticker of a stock (example: Microsoft ticker is MSFT)

## Notes on pdfkit
* requires _wkhtmltopdf_ to be installed 
* This is a setup for a Windows environment, not sure if it works in other operating systems.
* Set the path to your _wkhtmltopdf.exe_
* If you are having issues, add it to your PATH environmental variables
* Check the wkhtmltopdf github for more info: https://github.com/JazzCore/python-pdfkit/wiki/Installing-wkhtmltopdf
```
# Set your path in the create pdf function
os.environ['PATH'] += os.pathsep + 'C:\\.....\\bin'

config = pdfkit.configuration(wkhtmltopdf='C:\\......\\bin\\wkhtmltopdf.exe')
```