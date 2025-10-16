# Million Dollar Futures Dashboard

**Live Demo:** https://million-dollar.onrender.com/

An interactive dashboard to analyze futures structures for SOFR, SONIA, Euribor, CoRRA, ESTR, EFFR, EMP, NPC, VIX, and FVS

## Key Features

**1. Curve Views**  
Forward curve analysis with corresponding spreads (3mo, 6mo, 12mo), Butterfly (3mo, 6mo, 12mo), and Double fly (3mo, 6mo, 12mo) structures, plus non-quoted ratios such as difference of consecutive flies or ratios like 1:2 or 2:3

**2. Futures Chain Overview**  
One-sight view with customizable filters and sorting of structures. Includes all relevant metrics: percentile rank, Z-score, roll down and roll up, range, sparklines, daily change histograms, and other statistical metrics

**3. Heatmap Matrix View**  
All structures in a single view with switchable values and colorscale features. Click any cell to get general information of the selected contract along with recent movement sparklines and daily changes

**4. Cycle Classification**  
Classifies each day into 3 cycles: Hike cycle, Ease cycle, and Sideways based on user-set criteria. Analyze KDE distribution of each structure based on classification

Built using Dash, Plotly, and Bootstrap for a seamless and responsive experience

---

## Features Overview

✅ **Interactive plots and tables**  
✅ **Works directly with Excel data (SR3.xlsx)**  
✅ **Modular Python scripts for easier maintenance**  
✅ **Easy to run locally**

![Dashboard Preview](https://github.com/user-attachments/assets/b15a8711-3018-4fab+** installed and accessible in terminal
- **Pip** (Python package installer)  
- **Web browser** (Chrome, Edge, Firefox, etc.)

## Setup Instructions

### 1. Download the Project
Go to the GitHub repository: [Million-Dollar Repo](https://github.com/RatKush/Million-Dollar/tree/downloadable)

Download the ZIP and extract all files into a folder

### 2. Install Dependencies
Open terminal (Command Prompt on Windows, Terminal on macOS/Linux)

Navigate to the folder where requirements.txt is located (optional if you use combined command)

Run the installation command:

**Windows:**
```bash
pip install -r "C:\path\to\requirements.txt"
```

**macOS/Linux:**
```bash
pip3 install -r "/path/to/requirements.txt"
```

This will install all required Python packages to run the dashboard

### 3. Run the Dashboard

**Option A — Using VS Code:**
- Open the project folder in VS Code
- Click the Run button on dashboard.py OR open the VS Code terminal and type:
```bash
python dashboard.py
```

**Option B — Using Terminal:**
Navigate to your project folder:
```bash
cd "path_to_million_dollar_folder_where_you_saved"
```

Run the dashboard:
```bash
python dashboard.py
```

**💡 Shortcut — combine steps 1 & 2 in one line:**
```bash
cd "path_to_million_dollar_folder_where_you_saved" && python dashboard.py
```

### 4. Open in Browser
After running, you should see output similar to:
```
Dash is running on http://127.0.0.1:8050/
```

Open this URL in your browser to access the dashboard.  
If the port is different (e.g., 8060), use the port shown in the terminal

## Notes & Tips

- Ensure all scripts and data files are in the same folder
- Use Python 3.8+ to avoid compatibility issues  
- If running on macOS/Linux, you may need `python3` instead of `python`

## Contact

For questions or support, reach out to: **ratkush2023@gmail.com**
