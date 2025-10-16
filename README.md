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

Million Dollar Dashboard

A Python-based interactive dashboard built using Dash for visualizing and analyzing data from Excel files.

🚀 Features

Interactive plots and tables

Works directly with Excel data (SR3.xlsx)

Modular Python scripts for easier maintenance

Easy to run locally

📁 <img width="416" height="199" alt="image" src="https://github.com/user-attachments/assets/b15a8711-3018-4fab-ada3-9faa7b7a5ec3" />


🛠️ Prerequisites

Python 3.8+ installed and accessible in terminal

Pip (Python package installer)

Web browser (Chrome, Edge, Firefox, etc.)

📥 Setup Instructions
1. Download the Project

Go to the GitHub repository:
[Million-Dollar Repo](https://github.com/RatKush/Million-Dollar/tree/downloadable)

Download the ZIP and extract all files into a folder.

2. Install Dependencies

Open terminal (Command Prompt on Windows, Terminal on macOS/Linux)

Navigate to the folder where requirements.txt is located (optional if you use combined command)

Run the installation command:

Windows:

pip install -r "C:\path\to\requirements.txt"


macOS/Linux:

pip3 install -r "/path/to/requirements.txt"


This will install all required Python packages to run the dashboard.

3. Run the Dashboard

There are two options:

Option A — Using VS Code:

Open the project folder in VS Code.

Click the Run button on dashboard.py
OR open the VS Code terminal and type:

python dashboard.py


Option B — Using Terminal:

Navigate to your project folder:

cd "path_to_million_dollar_folder_where_you_saved"


Run the dashboard:

python dashboard.py


💡 Shortcut — combine steps 1 & 2 in one line:

cd "path_to_million_dollar_folder_where_you_saved" && python dashboard.py

4. Open in Browser

After running, you should see output similar to:

Dash is running on http://127.0.0.1:8050/


Open this URL in your browser to access the dashboard.

If the port is different (e.g., 8060), use the port shown in the terminal.

⚙️ Notes & Tips

Ensure all scripts and data files are in the same folder.

Use Python 3.8+ to avoid compatibility issues.

If running on macOS/Linux, you may need python3 instead of python.

📝 Contact

For questions or support, reach out to:
ratkush2023@gmail.com
