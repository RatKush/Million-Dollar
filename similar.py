import time
from typing import Optional, Union, Dict, Any
import pandas as pd
import logging
from str_cal import process_raw_data, serialize_dataframe



DEFAULT_FILES = ["SR3_ED_GEN.xlsm", "SR3.xlsx"]
DEFAULT_LOOKBACK = 250
def extract_raw_data(filename: str, lookback_prd: Union[str, int]) -> Dict[str, Any]:
    """CORRECTED: Extract raw data callback - simplified validation"""
    # Basic validation - return empty if invalid inputs
    if not filename or not lookback_prd:
        return {}
    
    try:
        lookback_prd_int = int(lookback_prd)
        if lookback_prd_int <= 0:
            return {}, None
        
        # Load and process data - FIXED: now returns tuple
        raw_df = process_raw_data(filepath=filename, lookback_prd=lookback_prd_int)
        if raw_df.empty:
            return {}, None
        
        # Serialize the raw data for storage
        try:
            ts = pd.to_datetime(raw_df.index[0], errors='coerce')
            latest_date = ts.strftime("%d-%m-%y") if pd.notnull(ts) else None
        except Exception as e:
            logging.warning(f"Could not parse latest date: {e}")
            latest_date = None

        serialized_raw_data = serialize_dataframe(raw_df)
        return serialized_raw_data, latest_date
        
    except Exception as e:
        logging.error(f"Error in extract_raw_data_callback for file {filename}: {e}")
        return {}, None

df_raw_data, latest_date = extract_raw_data(DEFAULT_FILES[0], DEFAULT_LOOKBACK)

print("\nRaw Data Information:")
print("-" * 50)
print("Latest date:", latest_date)
print("\nData Shape:", type(df_raw_data))
print("\nFirst few rows of data:")
print("-" * 50)
if isinstance(df_raw_data, dict):
    for key, value in df_raw_data.items():
        print(f"\nColumn: {key}")
        print(value[:3] if isinstance(value, list) else value)
else:
    print(df_raw_data)
print("\n" + "-" * 50)