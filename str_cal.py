# str_cal.py
import os
import pandas as pd
import numpy as np
from typing import Optional,Tuple, Dict, Any
import logging
from typing import Optional, Tuple

# str_cal.py (top of file)
DEFAULT_WINDOW = 21
DEFAULT_OUTLIER_K = 2.5
##############################################################
# DATA LOADING AND PREPROCESSING
##############################################################
def serialize_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Convert a pandas DataFrame to JSON-serializable dictionary - CORRECTED"""
    if df is None or df.empty:
        return {"data": [], "index": [], "columns": []}
    
    # Ensure index is serializable
    try:
        index_serialized = df.index.astype(str).tolist()
    except:
        index_serialized = list(range(len(df)))
    
    return {
        "data": df.values.tolist(),
        "index": index_serialized,
        "columns": df.columns.tolist()
    }

def serialize_series(series: pd.Series) -> Dict[str, Any]:
    """Convert a pandas Series to JSON-serializable dictionary - CORRECTED"""
    if series is None or series.empty:
        return {"values": [], "index": []}
    
    # Ensure index is serializable
    try:
        index_serialized = series.index.astype(str).tolist()
    except:
        index_serialized = list(range(len(series)))
    
    return {
        "values": series.values.tolist(),
        "index": index_serialized
    }


def get_rank(series, val):
    series = series.dropna().values
    if len(series) == 0:
        return np.nan
    rank = (np.sum(series < val) + 0.5 * np.sum(series == val)) / len(series)
    return rank * 100

def process_raw_data(filepath: str, lookback_prd: int) -> pd.DataFrame:
    if not isinstance(filepath, str) or not filepath.strip():
        raise ValueError("ERROR Filepath is missing")

    if not isinstance(lookback_prd, int) or lookback_prd <= 0:
        raise ValueError(f"ERROR  Lookback must be positive int, got {lookback_prd}")

    if lookback_prd > 10000:
        raise ValueError("ERROR  Lookback too large (>10000)")

    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"ERROR  File not found: {filepath}")

    if not os.access(filepath, os.R_OK):
        raise PermissionError(f"ERROR  No read permission: {filepath}")

    raw_df = load_data(lookback_prd, filepath)
    if raw_df.empty:
        raise ValueError("ERROR  Loaded data is empty")

    processed_df = fill_missing_values(raw_df)
    if processed_df.empty:
        raise ValueError("ERROR  Data empty after filling missing values")

    return processed_df


def process_structure_data(raw_df, comdty, win_local ,str_name):
    if raw_df.empty: 
        return pd.DataFrame(), "Raw data empty"
    
    try:
        if comdty == "SZI0":
            str_df = calculate_str(raw_df, get_ratio(str_name))
            if(str_name != "OUT"):
                str_df = str_df/100
        elif str_name == "OUT" and comdty in ["MEETS"]:
            default_ratio = pd.Series([1], index=[0], name="OUT")
            str_df = calculate_str(raw_df, default_ratio)
            str_df = rolling_bounds_filter(str_df, window=win_local, k=DEFAULT_OUTLIER_K)
        elif str_name != "OUT" and comdty in ["VIX", "FVS", "VIX-VOX"]:
            #default_ratio = pd.Series([1.0], index=[0], name="OUT")
            #print(str_name)
            str_df = calculate_str(raw_df, get_ratio(str_name))
            str_df = rolling_bounds_filter(str_df, window=win_local, k=DEFAULT_OUTLIER_K)
        else:
            str_df = calculate_str(raw_df, get_ratio(str_name))
            str_df = rolling_bounds_filter(str_df, window=win_local, k=DEFAULT_OUTLIER_K)
        
        return str_df

    except Exception as e:
        logging.error(f"process_str_df failed: {e}")
        return pd.DataFrame()


# fn to build only main series // rater then cal full str_df
def fn_main_series_only(raw_df,str_name,str_number, comdty, lookback_prd, DEFAULT_WINDOW, DEFAULT_OUTLIER_K):
    ratio= get_ratio(str_name)
    max_row= raw_df.shape[0] #280 i.e.  lookback
    max_col= raw_df.shape[1] #35  i.e. 
    # print( "col", max_col, "row", max_row)
    if(max_col < str_number+ len(ratio)-1):
        str_main_series= pd.Series()
    if comdty == "SZI0":
        str_main_series = pd.Series(raw_df.iloc[:, str_number-1:str_number-1+len(ratio)].values @ np.array(ratio),index=raw_df.index)
        if(str_name == "OUT"):
            str_main_series= str_main_series*100
    elif str_name == "OUT" and comdty in ["MEETS"]:
        default_ratio = pd.Series([100], index=[0], name="OUT")
        str_main_series = pd.Series(raw_df.iloc[:, str_number-1:str_number-1+len(default_ratio)].values @ np.array(default_ratio),index=raw_df.index)
        str_main_series = rolling_bounds_filter(str_main_series, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
    elif str_name == "OUT" and comdty in ["VIX", "FVS", "VIX-VOX"]:
        default_ratio = pd.Series([1.0], index=[0], name="OUT")
        str_main_series = pd.Series(raw_df.iloc[:, str_number-1:str_number-1+len(default_ratio)].values @ np.array(default_ratio),index=raw_df.index)
        str_main_series = rolling_bounds_filter(str_main_series, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
    else:
        str_main_series = pd.Series(raw_df.iloc[:, str_number-1:str_number-1+len(ratio)].values @ np.array(ratio),index=raw_df.index)
        str_main_series= str_main_series*100
        str_main_series = rolling_bounds_filter(str_main_series, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
    
    actual_lookback = min(lookback_prd, max_row)
    # Extract series (convert to 0-indexed)
    str_main_series = str_main_series.iloc[:actual_lookback]
    return  str_main_series


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values efficiently using vectorized operations."""
    
    if df.empty:
        return df
    
    df_filled = df.copy()
    
    # Count initial missing values
    initial_missing = df_filled.isna().sum().sum()
    
    if initial_missing == 0:
        return df_filled
    
    # Fill each numeric column individually (vectorized)
    for column in df_filled.select_dtypes(include=[np.number]).columns:
        if df_filled[column].isna().any():
            # Find first and last valid values
            non_null_mask = df_filled[column].notna()
            if non_null_mask.any():
                first_valid = non_null_mask.idxmax()
                last_valid = non_null_mask[::-1].idxmax()
                
                # Only interpolate between first and last valid
                if first_valid != last_valid:
                    df_filled.loc[first_valid:last_valid, column] = (
                        df_filled.loc[first_valid:last_valid, column]
                        .interpolate(method='linear')
                    )
    
    return df_filled


def load_data(lookback_prd: int, filepath: str = "SR3_ED_GEN.xlsm") -> pd.DataFrame:
    """Load structured curve data from Excel file."""
    
    # ===== STEP 1: INPUT VALIDATION =====
    if not isinstance(lookback_prd, int) or lookback_prd <= 0:
        print(f"ERROR Invalid lookback_prd: {lookback_prd}")
        return pd.DataFrame()
    
    if not isinstance(filepath, str) or not filepath.strip():
        print("ERROR Invalid filepath provided")
        return pd.DataFrame()
    
    if not os.path.exists(filepath):
        print(f"ERROR File not found: {filepath}")
        return pd.DataFrame()
    
     # ===== STEP 2: SAFE FILE READING WITH FALLBACKS =====
    try:
        df = None
        
        # Strategy 1: Try reading with row limit (faster)
        try:
            df = pd.read_excel(filepath, sheet_name=0, engine='openpyxl', nrows=100)
            print("DONE Read with row limit strategy")
        except Exception as e1:
            print(f"⚠️ Row limit strategy failed: {e1}")
            
            # Strategy 2: Try reading without row limit
            try:
                df = pd.read_excel(filepath, header=None)
                print("DONE Read with unlimited rows strategy")
            except Exception as e2:
                print(f"ERROR  All Excel strategies failed: {e1}, {e2}")
                return pd.DataFrame()
        
        # Early validation
        # Early validation with SAFE shape checking
        try:
            if df is None or df.empty:
                print("ERROR DataFrame is None or empty")
                return pd.DataFrame()
            
            # Safe shape extraction
            try:
                rows, cols = df.shape
                rows, cols = int(rows), int(cols)  # Ensure integers
            except (ValueError, TypeError) as e:
                print(f"ERROR Invalid DataFrame shape: {e}")
                return pd.DataFrame()
            
            if rows < 2 or cols < 2:
                print(f"ERROR Insufficient data: {rows} rows, {cols} columns")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"ERROR DataFrame validation failed: {e}")
            return pd.DataFrame()

        
        # ===== STEP 3: SAFE COLUMN PROCESSING =====
        # Limit lookback to prevent memory issues
        #safe_lookback = min(lookback_prd, 800)  
        safe_lookback = max(lookback_prd, 5)  
        max_cols = min(int(df.shape[1])- 1, safe_lookback + 30)
        
        if max_cols <= 0:
            print("ERROR  No valid columns found")
            return pd.DataFrame()
        
        df_subset = df.iloc[:, :max_cols + 1].copy()
        
        # ===== STEP 4: ROBUST DATE PROCESSING =====
        date_row = df_subset.iloc[0, 1:]
        dates = None
        
        # Strategy 1: Excel serial dates (most common)
        try:
            date_values = pd.to_numeric(date_row, errors='coerce')
            valid_mask = ~pd.isna(date_values)
            if valid_mask.any():
                dates = pd.to_datetime(
                    date_values[valid_mask], 
                    unit='D', 
                    origin='1899-12-30', 
                    errors='coerce',
                )
                dates = dates.dropna()
                if len(dates) >= 5:
                    print("DONE Using Excel serial dates")
                else:
                    dates = None
        except Exception as e:
            print(f"⚠️ Excel date parsing failed: {e}")
        
        # Strategy 2: Direct datetime parsing
        if dates is None or len(dates) < 5:
            try:
                dates = pd.to_datetime(date_row, errors='coerce')
                dates = dates.dropna()
                if len(dates) >= 5:
                    print("DONE Using direct datetime parsing")
                else:
                    dates = None
            except Exception as e:
                print(f"⚠️ Direct datetime parsing failed: {e}")
        
        # Strategy 3: Synthetic dates (fallback)
        if dates is None or len(dates) < 5:
            print("⚠️ Using synthetic dates as fallback")
            dates = pd.date_range(
                start='2020-01-01', 
                periods=len(date_row), 
                freq='D'
            )
        
        # ===== STEP 5: CONTRACT PROCESSING =====
        contracts = df_subset.iloc[1:, 0].dropna()
        if contracts.empty:
            print("ERROR No contracts found")
            return pd.DataFrame()
        
        # ===== STEP 6: SAFE DIMENSION MATCHING =====
        n_contracts = len(contracts)
        n_dates = len(dates)
        
        # Calculate safe dimensions
        max_data_rows = min(n_contracts, df_subset.shape[0] - 1)
        max_data_cols = min(n_dates, df_subset.shape[1] - 1)
        
        if max_data_rows == 0 or max_data_cols == 0:
            print("ERROR  No valid data dimensions")
            return pd.DataFrame()
        
        # Extract price data with safe bounds
        price_data = df_subset.iloc[1:max_data_rows+1, 1:max_data_cols+1].values
        
        # ===== STEP 7: CREATE OUTPUT DATAFRAME =====
        out_df = pd.DataFrame(
            price_data.T,  # Transpose to get dates as rows
            index=dates[:max_data_cols],
            columns=contracts.iloc[:max_data_rows].values
        )
        
        # ===== STEP 8: CLEAN AND OPTIMIZE =====
        # Clean column names efficiently
        out_df.columns = (
            out_df.columns.astype(str)
            .str.replace(' Comdty', '', regex=False)
            .str.replace(' Index', '', regex=False)
            .str.strip()
        )
        
        # Convert to numeric and handle errors gracefully
        numeric_cols = []
        for col in out_df.columns:
            try:
                out_df[col] = pd.to_numeric(out_df[col], errors='coerce')
                numeric_cols.append(col)
            except Exception as e:
                print(f"⚠️ Skipping non-numeric column {col}: {e}")
        
        if not numeric_cols:
            print("ERROR  No numeric columns found")
            return pd.DataFrame()
        
        # Keep only numeric columns
        out_df = out_df[numeric_cols]
        
        # Remove empty rows/columns
        out_df = out_df.dropna(how='all').dropna(axis=1, how='all')
        
        print(f"DONE Successfully loaded data: {out_df.shape}")
        return out_df
        
    except Exception as e:
        print(f"ERROR  Critical error loading {filepath}: {str(e)}")
        return pd.DataFrame()

################################################################# outliers removal fn ######################
## 2  outliers  for a df  # rolling mean ± k*std.         ### not that robust ----- sometimes outliers hides themselves due to high std causeed by themselves
def process_series(series, window=DEFAULT_WINDOW , k=DEFAULT_OUTLIER_K, min_periods  = 5):
    series = pd.to_numeric(series, errors='coerce')
    if series.count() < min_periods:
        return series
    # Keep track of where the original NaNs were
    original_nans = series.isna()
    rolling_mean = series.rolling(window=window, center=True,  min_periods=5).mean()
    rolling_std = series.rolling(window=window, center=True,  min_periods=5).std()
    upper_bound = rolling_mean + k * rolling_std
    lower_bound = rolling_mean - k * rolling_std
    # Replace only where bounds are valid (not NaN)
    mask = (series < lower_bound) | (series > upper_bound)
    filtered = series.copy()
    filtered[mask] = np.nan
    
     # Interpolate to fill only the new NaNs created by the filter
    interpolated = filtered.interpolate(method='linear', limit_direction='both', axis=0)

    # Re-apply the original NaNs so the tail remains empty
    interpolated[original_nans] = np.nan
    
    return interpolated


def rolling_bounds_filter(df, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K):
    if isinstance(df, pd.Series):
        return process_series(df, window=window, k=k)
    elif isinstance(df, pd.DataFrame):
        return df.apply(process_series, window=window, k=k)
    else:
        raise TypeError("Input must be a pandas Series or DataFrame")

####3 IQR
def process_series_iqr(series, window=DEFAULT_WINDOW, k=1.5,  min_periods  = 5): #####less ier k
    """
    Processes a single pandas Series to filter outliers using the rolling IQR method.
    
    This function identifies outliers, replaces them with NaN, interpolates the new 
    gaps, and then restores any NaN values that existed in the original series.
    """
    # Ensure data is numeric, converting non-numeric values to NaN
    series = pd.to_numeric(series, errors='coerce')
    if series.count() < min_periods:
        return series
    # Keep track of where the original NaNs were to restore them later
    original_nans = series.isna()

    # Calculate rolling Q1 (25th percentile) and Q3 (75th percentile)
    q1 = series.rolling(window=window, center=True, min_periods=5).quantile(0.25)
    q3 = series.rolling(window=window, center=True, min_periods=5).quantile(0.75)
    
    # Calculate the rolling Interquartile Range (IQR)
    iqr = q3 - q1
    
    # Define the upper and lower outlier boundaries
    upper_bound = q3 + k * iqr
    lower_bound = q1 - k * iqr
    
    # Create a boolean mask to identify outliers
    outlier_mask = (series < lower_bound) | (series > upper_bound)
    
    # Create a copy of the series and replace outliers with NaN
    filtered = series.copy()
    filtered[outlier_mask] = np.nan
    
    # Interpolate to fill only the new gaps created by the filter
    interpolated = filtered.interpolate(method='linear', limit_direction='both', axis=0)

    # Re-apply the original NaNs to ensure the tail remains empty
    interpolated[original_nans] = np.nan
    
    return interpolated


def rolling_iqr_filter(df, window=DEFAULT_WINDOW,  k=2):####### diff outlieer K
    if isinstance(df, pd.Series):
        return process_series_iqr(df, window=window, k=k)
    elif isinstance(df, pd.DataFrame):
        return df.apply(process_series_iqr, window=window, k=k)
    else:
        raise TypeError("Input must be a pandas Series or DataFrame")

########################################################################################################################




def get_ratio(ratio_name):
    ratio = ratio_table.loc[ratio_name]
    return ratio[:next((i for i, x in enumerate(ratio) if pd.isna(x)), len(ratio))]



def calculate_str(df, ratio):
    str_data = []
    max_cols = 0
    for _, row in df.iterrows():
        str_row = _rolling_sumproduct(row, ratio)
        str_data.append(str_row)
        max_cols = max(max_cols, len(str_row))
    str_data = [row + [np.nan] * (max_cols - len(row)) for row in str_data]
    #print("calculated str")
    return pd.DataFrame(str_data, index=df.index, columns=df.columns[:max_cols])


def _rolling_sumproduct(row, ratio):
    ratio_len = len(ratio)
    return [
        100 * np.dot(row[i:i + ratio_len], ratio)
        for i in range(len(row) - ratio_len + 1)
        if not np.isnan(row[i:i + ratio_len]).any()
    ]



##############################################################
# STRUCTURE RATIO DEFINITIONS AND ENGINE
##############################################################
index = [
    "OUT", "S3", "S6", "S12", "L3", "L3(II)", "L6(I)", "L6", "L6(III)", "L6(IV)",
    "L12(I)", "L12(II)", "L12(III)", "L12", "D3", "D3(II)", "D6(I)", "D6", "D6(III)", "D6(IV)",
    "D12(I)", "D12(II)", "D12(III)", "D12","E3","E6(I)", "E6(II)", "1X L6- 2X L6(n+1)", "2X L6- 3X L6(n+1)", "1X L6- 2X L6(n+2)", "2X L6- 3X L6(n+2)",
    "1X Out- 2X O(n+1)", "2X Out- 1X O(n+1)", "2X Out- 3X O(n+1)", "3X Out- 2X O(n+1)", "1X S1- 2X S1(n+1)", "2X S1n- 1X S1(n+1)", "2X S1- 3X S1(n+1)", "3X S1- 2X S1(n+1)"
]

ratio= [
    [0.01],                                     # "Out"     i=0 
    [1, -1],                                    # "S3"      i=1
    [1, 0, -1],                                 # "S6"      i=2
    [1, 0, 0, 0, -1],                           # "S12"     i=3
    [1, -2, 1],                                 # "L3"      i=4
    [1, -1, -1, 1],                             # "L3(II)"  i=5
    [1, -1, -1, 1],                             # "L6(I)"   i=6
    [1, 0, -2, 0, 1],                           # "L6"      i=7
    [1, 0, -1, -1, 0, 1],                       # "L6(III)" i=8
    [1, 0, -1, 0, -1, 0, 1],                    # "L6(IV)"  i=9
    [1, -1, 0, 0, -1, 1],                       # "L12(I)"  i=10
    [1, 0, -1, 0, -1, 0, 1],                    # "L12(II)" i=11
    [1, 0, 0, -1, -1, 0, 0, 1],                 # "L12(III)"i=12
    [1, 0, 0, 0, -2, 0, 0, 0, 1],               # "L12"     i=13
    [1, -3, 3, -1],                             # "D3"      i=14
    [1, -2, 0, 2, -1],                          # "D3(II)"  i=15
    [1, -1, -2, 2, 1, -1],                      # "D6(I)"   i=16
    [1, 0, -3, 0, 3, 0, -1],                    # "D6"      i=17
    [1, 0, -2, -1, 1, 2, 0, -1],                # "D6(III)" i=18
    [1, 0, -2, 0, 0, 0, 2, 0, -1],              # "D6(IV)"  i=19
    [1, -1, 0, 0, -2, 2, 0, 0, 1, -1],          # "D12(I)"  i=20
    [1, 0, -1, 0, -2, 0, 2, 0, 1, 0, -1],       # "D12(II)" i=21
    [1, 0, 0, -1, -2, 0, 0, 2, 1, 0, 0, -1],    # "D12(III)"i=22
    [1, 0, 0, 0, -3, 0, 0, 0, 3, 0, 0, 0, -1],  # "D12"     i=23
    [1,-4,6,-4,1],                              # "E3"      i=24
    [1, -1, -3, 3, 3, -3, -1, 1],               # "E6(I)"   i=25
    [1, 0, -4, 0, 6, 0, -4, 0, 1],              # "E6(II)"  i=26

    [1, -2, -2, 4, 1, -2],                      # 1X L6- 2X L6(n+1)  i=27
    [2, -3, -4, 6, 2, -3],                      # 2X L6- 3X L6(n+1)  i=28
    [1, 0, -4, 0, 5, 0, -2],                    # 1X L6- 2X L6(n+2)  i=29
    [2, 0, -7, 0, 8, 0, -3],                    # 2X L6- 3X L6(n+2)  i=30

    [1,-2],                                     # "1X On- 2X On+1"  i=31
    [2, -1],                                    # "2X On- 1X On+1"  i=32
    [2, -3],                                    # "2X On- 3X On+1"  i=33
    [3, -2],                                    # "3X On- 2X On+1"  i=34

    [1,-3,2],                                   # "1X S1n- 2X S1n+1"  i=35
    [2,-3,1],                                   # "2X S1n- 1X S1n+1"  i=36
    [2,-5,3],                                   # "2X S1n- 3X S1n+1"  i=37
    [3,-5,2],                                   # "3X S1n- 2X S1n+1"  i=38                 
]

ratio_table = pd.DataFrame(ratio, index=index)

#print(get_ratio("S3"))
# out_df, str_df, series,cmdty, str_name, str_num= process_structure("SR3.xlsx", "S3", 8, 20, 20)
# df= rolling_bounds_filter(out_df, window=21, k=2.5)
# print(out_df)


################################### fetch effr ######################################
def fetch_rates_cycle(lookback_prd, filepath= "SR3_ED_GEN.xlsm", sheetname= "treasuries rates"):
    df = pd.read_excel(filepath, sheet_name = sheetname, header= None)
     
    max_cols = min(df.shape[1]-1, lookback_prd+22)
    df = df.iloc[0:25, 1 : max_cols]

    #columns names  from top row i.e row 3
    xl_dates = pd.to_numeric(df.iloc[2, 0:].values, errors='coerce')
    dates = pd.to_datetime(xl_dates, unit='D', origin='1899-12-30')

    # final data container
    rates_df= df.iloc[[3,9,15,21]].copy()  # 2Yr, 5Yr, 10Yr, rates
    rates_df.index = ["2Yr", "5Yr", "10Yr", "Rates"]
    y2y10= (df.iloc[3]- df.iloc[15])
    rates_df.loc['2y10y'] = y2y10
    rates_df.columns= dates
    for i in range(len(rates_df) - 1): # passing all except rates row
        rates_df.iloc[i]= rolling_bounds_filter(rates_df.iloc[i], window=21, k=DEFAULT_OUTLIER_K)

    max_cols = min(rates_df.shape[1]-1 , lookback_prd)
    rates_df= rates_df.iloc[:, 0:max_cols].copy()
    #print(rates_df.head(), rates_df.shape)
    
    return rates_df


# Helper function for structure calculations  
def process_help_calculation(comdty, out_df, base_str, lookback_prd, curve_length, DEFAULT_WINDOW, DEFAULT_OUTLIER_K ):
    """Helper function for structure calculations"""
    try:
        # ✅ FIXED: process_str_df returns (DataFrame, error_msg) tuple
        str_df, error_msg = process_str_df(out_df, comdty, base_str, DEFAULT_WINDOW, DEFAULT_OUTLIER_K )
        
        if str_df.empty:
            print(f"Warning: Empty structure DataFrame for {comdty}-{base_str}")
            return pd.DataFrame(), comdty
            
        # Return the processed dataframe and commodity
        return str_df.head( lookback_prd), comdty
        
    except Exception as e:
        print(f"Error in helper calculation: {e}")
        return pd.DataFrame(), comdty


def process_str_df(raw_df: pd.DataFrame, comdty: str, str_name: str,DEFAULT_WINDOW, DEFAULT_OUTLIER_K  ) -> Tuple[pd.DataFrame, Optional[str]]:
    if raw_df.empty:
        return pd.DataFrame(), "Raw data empty"

    try:
        if comdty == "SZI0":

            str_df = calculate_str(raw_df, get_ratio(str_name))
        elif str_name == "Out" and comdty in ["MEETS", "SZI0"]:
            default_ratio = pd.Series([1.0], index=[0], name="Out")
            str_df = calculate_str(raw_df, default_ratio)
            str_df = rolling_bounds_filter(str_df, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
        else:
            str_df = calculate_str(raw_df, get_ratio(str_name))
            str_df = rolling_bounds_filter(str_df, window=DEFAULT_WINDOW, k=DEFAULT_OUTLIER_K)
        
        return str_df, None

    except Exception as e:
        logging.error(f"process_str_df failed: {e}")
        return pd.DataFrame(), f"ERROR Failed processing {comdty}-{str_name}: {e}"

