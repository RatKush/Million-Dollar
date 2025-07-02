# Million-Dollar
Interactive dashboard for analyzing SOFR/ SONIA/ Euribor/ CoRRA/ EFFR futures structures: curve views, cycle classification, KDE overlays, and structure breakdowns. Built with Dash, Bootstrap, and Plotly.

To run Million Dollar at local:-
first prepare data in mentioned format- 
data format in excel--
![image](https://github.com/user-attachments/assets/ccf74a35-3e4f-4c81-95e3-d68f4fb7b355)


Row 1: Contains headers or placeholders for data, Anything you want or Empty row 
Row 2: Displays dates from 2nd column onwards in "Serial Date" format (e.g., 45828, 45827) in decreasing order representing specific days. Latest data is in 2nd column
column 1: contain generic contract number with commodity name (from 3rd row) e.g., SOFR1 (A3) , SOFR2 (A4), SOFR3 (A5)
Rows 3/ column 2: form B3 cell- Include financial data for commodity contracts. Each row shows numerical values (e.g., 95.67125, 95.665) likely representing prices or rates across the dates in row 2.

ready to run:
a. have all files in a folder
b. there is a sample data set provided (SR3.xlsx) keep it in the same folder or keep your own data in illistrtive data's format 
c. cmd> pip install -r path_of_requirements.txt
d. run dashboard.py
(terminal>> python dashboard.py
e. you should get a url at output i.e. http://127.0.0.1:8050/
