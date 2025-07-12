# str_cal.py
import os
import pandas as pd
import numpy as np
import difflib


##############################################################
# DATA LOADING AND PREPROCESSING
##############################################################


def extract_comdty(filepath):
    text_lower = filepath.lower()
    match_pool= ["SR3_ED","sr3", "sr1", "so3", "er", "er3", "corra", "szi0", "meeting", "meet", "sonia", "sofr", "euribor","meetings", "sa3", "saron", "vix vs voxx", "vix", "vx", "VOXX", "vol", "FVS", "fvs", "vstoxx"]
    #best_match = difflib.get_close_matches(text_lower, match_pool, n=1, cutoff=0.4)
    mapping= {
        "SR3_ED": "SR3_ED", "sr3": "SR3", "sr1": "SR1", "so3": "S03", "er": "ER", "er3": "ER", "corra":"CoRRa", "szi0":"SZI0", "meeting": "meets", "meet": "meets", "sonia":"SO3", "sofr":"SR3", "euribor":"ER","meetings":"meets", "sa3":"SA3", "saron" :"SA3", "eurodollar":"ED", "ed": "ED", "vix": "VIX", "vx":"VIX", "VOXX": "FVS" , "FVS":"FVS", "fvs":"FVS", "vstoxx":"FVS", "vol":"VIX", "vix vs voxx": "VIX- VOXX"
    }
     # Custom similarity ranking
    scored = []
    for key in match_pool:
        score = difflib.SequenceMatcher(None, text_lower, key).ratio()
        
        # Optional boost if key is a substring
        if key in text_lower:
            score += 0.2  # boost for substring match
        
        scored.append((score, key))

    # Sort by descending score
    scored.sort(reverse=True)

    best_score, best_key = scored[0]
    #print(mapping.get(best_key), best_score)
    if best_score > 0.4:  # Adjust as needed
        return mapping.get(best_key)

    # fallback: strip extension
    return filepath.split('.')[0]



def extract_series(str_df, str_number=8, lookback_prd=250):
    """
    Extract a structure's time series from the DataFrame.
    If str_number exceeds the number of columns, fallback to max possible.
    Returns (series, msg) tuple.
    """
    max_col = str_df.shape[1]
    fallback_msg = None

    if str_number > max_col:
        str_number = max_col
        fallback_msg = f"Selected structure number was too high. Fallback to STR-{str_number} (max available)."

    lookback_prd = min(lookback_prd, str_df.shape[0])
    series = str_df.iloc[:, str_number - 1].iloc[:lookback_prd]
    series.index = pd.to_datetime(series.index)

    return series.dropna()


def process_help_calculation(comdty, out_df, str_name, lookback_prd, curve_length):
    if comdty == "SZI0":
        str_df = calculate_str(out_df, get_ratio(str_name))
    elif str_name== "Out" and (comdty== "meets" or comdty== "SZI0"):
        str_df = calculate_str(out_df, pd.Series([1.0], index=[0], name='Out')) # defultis at 0.01 hemce here for meeting data set it to {1}
        str_df= rolling_bounds_filter(str_df, window=21, k=2.5)
    else:
        str_df = calculate_str(out_df, get_ratio(str_name))
        #str_df = remove_outliers(str_df, lower_quantile=0.01, upper_quantile=0.99)
        str_df= rolling_bounds_filter(str_df, window=21, k=2.5)
    

    # Ensure curve_length is a valid integer and within bounds
    try:
        curve_length = int(curve_length)
    except (TypeError, ValueError):
        curve_length = str_df.shape[1]  # fallback to full width

    curve_length = min(curve_length, str_df.shape[1])
    str_df = str_df.iloc[:, :curve_length]


    # Ensure lookback_prd is a valid integer and within bounds
    try:
        lookback_prd = int(lookback_prd)
    except (TypeError, ValueError):
        lookback_prd = str_df.shape[0] - 1  # fallback to all rows

    lookback_prd = max(0, min(lookback_prd, str_df.shape[0] - 1))
    str_df = str_df.head(lookback_prd)

    #print(comdty)
    return str_df, comdty


def process_structure(filepath, str_name, str_number, lookback_prd, curve_length):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File '{filepath}' not found.")
    out_df = fill_missing_values(load_data(lookback_prd, filepath ))
    comdty = extract_comdty(filepath)
    str_df, comdty= process_help_calculation(comdty, out_df, str_name, lookback_prd, curve_length)
    
    series = extract_series(str_df, str_number=str_number, lookback_prd=lookback_prd)
    return out_df,str_df, series, comdty,str_name,str_number


def fill_missing_values(df):
    """Interpolate missing values in the DataFrame without changing column order."""
    
    def _fill_mid_nan(row):
        notna = row.notna()
        if notna.sum() == 0:
            return row

        first_notna = notna.idxmax()
        last_notna = notna[::-1].idxmax()
        mid = row.loc[first_notna: last_notna]
        interpolation_mid = mid.interpolate(method='linear', limit_direction='both', axis=0)
        row.update(interpolation_mid.bfill())

        return row[df.columns]

    print("data loaded")
    return df.apply(_fill_mid_nan, axis=1)


def load_data(lookback_prd, filepath="SR3_ED.xlsxm"):
    """
    Load structured curve data from Excel, trimming to lookback_prd columns 
    for speed. Returns a DataFrame indexed by date, with one column per contract.
    """
    df = pd.read_excel(filepath, sheet_name=0)
    
    max_cols = min(df.shape[1] - 1, lookback_prd+21)
    df = df.iloc[:, 0 : max_cols + 1]
    
    xl_dates = pd.to_numeric(df.iloc[0, 1:].values, errors='coerce')
    dates = pd.to_datetime(xl_dates, unit='D', origin='1899-12-30')
    
    contracts = df.iloc[1:, 0].values
    prices = df.iloc[1:, 1:].values 
    out_curve_df = pd.DataFrame(prices.T, index=dates, columns=contracts)
    out_curve_df.columns = out_curve_df.columns.str.replace(" Comdty", "", regex=False)
    out_curve_df = out_curve_df.dropna(how='all').apply(pd.to_numeric, errors='coerce')
    #print(out_curve_df)
    return out_curve_df



def remove_outliers(df, lower_quantile=0.01, upper_quantile=0.99):
    q_low = df.quantile(lower_quantile)
    q_high = df.quantile(upper_quantile)
    mask = (df < q_low) | (df > q_high)
    df_cleaned = df.mask(mask)
    #print(df.head())
    print("CALCULATED")
    return df_cleaned.interpolate(method='linear', limit_direction='both', axis=0)

## use it in place of remove  outliers  for a df  # rolling mean ± k*std.

def process_series(series, window=21, k=2.5):
    series = pd.to_numeric(series, errors='coerce')
    rolling_mean = series.rolling(window=window, center=True,  min_periods=5).mean()
    rolling_std = series.rolling(window=window, center=True,  min_periods=5).std()
    upper_bound = rolling_mean + k * rolling_std
    lower_bound = rolling_mean - k * rolling_std
    # Replace only where bounds are valid (not NaN)
    mask = (series < lower_bound) | (series > upper_bound)
    filtered = series.copy()
    filtered[mask] = np.nan
    
    return filtered.interpolate(method='linear', limit_direction='both', axis=0)


def rolling_bounds_filter(df, window=21, k=2.5):
    if isinstance(df, pd.Series):
        return process_series(df, window=window, k=k)
    elif isinstance(df, pd.DataFrame):
        return df.apply(process_series, window=window, k=k)
    else:
        raise TypeError("Input must be a pandas Series or DataFrame")








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
    "Out", "S3", "S6", "S12", "L3", "L3(II)", "L6(I)", "L6", "L6(III)", "L6(IV)",
    "L12(I)", "L12(II)", "L12(III)", "L12", "D3", "D3(II)", "D6(I)", "D6", "D6(III)", "D6(IV)",
    "D12(I)", "D12(II)", "D12(III)", "D12","E3","E6(I)", "E6(II)", "1X Sn- 2X Sn+1", "2X Sn- 1X Sn+1", "2X Sn- 3X Sn+1", "3X Sn- 2X Sn+1"
]

ratio= [
    [0.01],
    [1, -1],
    [1, 0, -1],
    [1, 0, 0, 0, -1],
    [1, -2, 1],
    [1, -1, -1, 1],
    [1, -1, -1, 1],
    [1, 0, -2, 0, 1],
    [1, 0, -1, -1, 0, 1],
    [1, 0, -1, 0, -1, 0, 1],
    [1, -1, 0, 0, -1, 1],
    [1, 0, -1, 0, -1, 0, 1],
    [1, 0, 0, -1, -1, 0, 0, 1],
    [1, 0, 0, 0, -2, 0, 0, 0, 1],
    [1, -3, 3, -1],
    [1, -2, 0, 2, -1],
    [1, -1, -2, 2, 1, -1],
    [1, 0, -3, 0, 3, 0, -1],
    [1, 0, -2, -1, 1, 2, 0, -1],
    [1, 0, -2, 0, 0, 0, 2, 0, -1],
    [1, -1, 0, 0, -2, 2, 0, 0, 1, -1],
    [1, 0, -1, 0, -2, 0, 2, 0, 1, 0, -1],
    [1, 0, 0, -1, -2, 0, 0, 2, 1, 0, 0, -1],
    [1, 0, 0, 0, -3, 0, 0, 0, 3, 0, 0, 0, -1],
    [1,-4,6,-4,1],
    [1, -1, -3, 3, 3, -3, -1, 1],
    [1, 0, -4, 0, 6, 0, -4, 0, 1],
    [1,-3,2],
    [2,-3,1],
    [2,-5,3],
    [3,-5,2],
]

ratio_table = pd.DataFrame(ratio, index=index)

#print(get_ratio("S3"))
# out_df, str_df, series,cmdty, str_name, str_num= process_structure("SR3.xlsx", "S3", 8, 20, 15)
# df= rolling_bounds_filter(out_df, window=21, k=2.5)
# print(out_df)
