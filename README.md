# Million-Dollar https://million-dollar.onrender.com/
Million Dollar Futures Dashboard

An interactive dashboard to analyze futures structures for SOFR / SONIA / Euribor / CoRRA / ESTR / EFFR / EMP / NPC / VIX / FVS.

Key features include:
#1. Curve views: forward curve and its analysis corresponding to many quoted i.e. spread(3mo, 6mo, 12mo), Butterfly (3mo, 6mo, 12mo) and Double fly (3mo, 6mo, 12mo) as well as non quoted ratios such as differance of consecutive flies or in ratio such as 1:2 or 2:3 

#2. Fut chain one sight view with filter and sorting customisable of strucutres along with all related matrics of interest i.e. percentile rank, Z  score , roll down and roll up, range, Sparkline, daily changes histogram, and many other statistical matrics.

#3. heatmap Matrix view of all strucutres in a single view with switchable values and colorscale feature. 
On click any cell will give you all the general inforamtion of the clicked contract along with its recent movement Sprakline and daily changes.

#4. Cycle classification: classifies ch day in 3 cycles i.e. Hike cycle, Ease cycle, and Sideways based on users set criteria and based on the classification can analyse KDE distribution of each strucuture. 

Built using Dash, Plotly, and Bootstrap for a seamless and responsive experience.
---

🚀 How to Run Locally

1. Setup Instructions
Ensure dashboard.py, requirements.txt,other python scripts and your excel data file (e.g., SR3.xlsx) are in the same directory.

1a. Download ZIP from https://github.com/RatKush/Million-Dollar/tree/downloadable repo and extract all and save in a folder
1b. Download python in your system, if already installed then leave this step
1c. Install Dependencies 
	copy path of requirements.txt
	go to terminal i> for windows "pip install -r path_to_requirements_txt" ii> for macos "pip3 install -r path_to_requirements_txt"
1d. Open folder in VS Code and click on Run button on dashboard.py file in VS Code/ any other IDE OR 
	in VS Code terminal write "python dashboard.py" and hit enter/return OR
	go to terminal and write "cd path_to_million_dollar_folder_where_you_saved" then enter then "python dashboard.py"

1e. Open in Browser:
	you must get this output in terminal:
	Dash is running on http://127.0.0.1:8050/ OR may be any other port i.e. 8060 
	Click on the url or just copy paste in you browser 

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
Dependencies are listed in requirements.txt



