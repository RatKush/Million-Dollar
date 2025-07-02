# Million-Dollar
Million Dollar Futures Dashboard

An interactive dashboard to analyze futures structures for SOFR / SONIA / Euribor / CoRRA / EFFR / VIX / FVS.
Key features include:

Curve views

Cycle classification

KDE overlays

Structure breakdowns


Built using Dash, Plotly, and Bootstrap for a seamless and responsive experience.


---

🚀 How to Run Locally

1. Prepare Your Data

![image](https://github.com/user-attachments/assets/ccf74a35-3e4f-4c81-95e3-d68f4fb7b355)
Your dataset should be in Excel format and follow this structure:

	A	B (latest date)	C (older date)	...

1	(any text or leave empty)	(dates in serial format like 45828)	...	
2	SOFR1	95.67125	...	
3	SOFR2	95.665	...	
...	...	...	...	


Notes:

Row 1: Header or placeholder (can be empty)

Row 2: Dates in Excel serial format, decreasing from left to right (latest date in column B)

Column A: Commodity + Contract ID (e.g., SOFR1, SOFR2...)

Cells from B3 onwards: Numerical data for each contract over time


A sample file (SR3.xlsx) is provided in the repo for reference.


---

2. Setup Instructions

a. Place All Files Together

Ensure dashboard.py, requirements.txt,other python scripts and your data file (e.g., SR3.xlsx) are in the same directory.

b. Install Dependencies

pip install -r requirements.txt

c. Run the App

python dashboard.py

d. Open in Browser

Once the server starts, open the displayed URL, typically:

http://127.0.0.1:8050/


---

📁 File Structure

project_folder/
│
├── dashboard.py
├── requirements.txt
├── other python scripts
├── SR3.xlsx  ← (or your own dataset)


---

📌 Dependencies

Make sure you have Python 3.7+ installed.
Dependencies are listed in requirements.txt and include:

dash

plotly

pandas

openpyxl

numpy

dash-bootstrap-components



