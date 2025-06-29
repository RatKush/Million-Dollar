import pandas as pd
import openpyxl

# Load the Excel file
filename= "2023_OBC-NCL_6_ALL_ALL.xlsx"
first_sheet = filename.split('_')[0]
df = pd.read_excel(filename, sheet_name=first_sheet)
pd.set_option('display.max_columns', None)
print(df.iloc[0:1])
pd.reset_option('display.max_columns')

#remove IITs # Filter: Keep rows where 'A' column does NOT contain the substring
substring = "Indian Institute  of Technology"
df = df[~df.iloc[:, 0].astype(str).str.contains(substring, na=False)]

substring = "Indian Institute of Technology"
df = df[~df.iloc[:, 0].astype(str).str.contains(substring, na=False)]

substring = "Female-only"
df = df[~df.iloc[:, 4].astype(str).str.contains(substring, na=False)]

# Build a mask that keeps rows where the cell in column_to_check is NOT exactly "JK"
mask_keep = df.iloc[:, 2].astype(str) != "JK"
df = df[mask_keep].copy()

mask_keep = df.iloc[:, 2].astype(str) != "GO"
df = df[mask_keep].copy()

# add city column
df['city'] = (df.iloc[:, 0].astype(str).str.rsplit(' ', n=1).str[-1])

col0_value = "HS"
allowed_col1 = ["Bhopal", "Jabalpur", "Gwalior"]
mask_keep = ~(
    (df.iloc[:, 2].astype(str) == col0_value)  # column 0 exactly "HS"
    & ~(df['city'].astype(str).isin(allowed_col1))  # column 1 is NOT in ["bhopal","jabal"]
)
df = df[mask_keep].copy()


# The exact combination to remove
combo = ("OS", "Bhopal")
mask = (df.iloc[:, 2] == combo[0]) & (df['city'] == combo[1])
df = df[~mask].copy()

filename= "FILTERED_"+ filename+ ".xlsx"
df.to_excel(filename, index=False)
print("saved to 'Filteredxxxxxx.xlsx'")

