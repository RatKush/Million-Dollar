from str_cal import  rolling_bounds_filter,fill_missing_values,load_data, index, get_ratio
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from scipy.stats import percentileofscore


 # removed rest unconventional structures

###### build button##########################################################

def get_button_class_tab7(is_active: bool) -> str:
    base = "tab7-button me-2"
    return base + " selected" if is_active else base

def build_button_tab7(label, id, active=False):
    return dbc.Button(
        label,
        id=id,
        className=get_button_class_tab7(active), 
        n_clicks=0
    )

####################### df computation ###############################################
structure_names= index[0:27]
def compute_3d_structure(out_df: pd.DataFrame, structure_names= structure_names , local_win=21, curve_length=15) -> pd.DataFrame:
    """
    Efficiently compute a MultiIndex DataFrame with shape (Date, Structure, Contract).
    
    - Z axis: Dates (depth)
    - X axis: Structure names
    - Y axis: Contracts
    - Values: Weighted structure results
    
    Returns a long-form pandas DataFrame with a MultiIndex.
    """

    all_frames = []  # Temporary list to store DataFrames for each structure
    dates = out_df.index[:local_win]  # Only use local window of most recent dates
    contracts = out_df.columns         # All contract labels, e.g., ['EDU5', 'EDZ5', ...]

    # Loop over each structure (e.g., L3, L6, L12...)
    for struct in structure_names:
        weights = np.array(get_ratio(struct))  # Convert the structure ratio into a NumPy array
        n = len(weights)                       # Length of the structure (e.g., 3 for butterfly)

        struct_data = []  # To store daily results for this structure

        # Loop over each date in the rolling window
        for date in dates:
            row = out_df.loc[date].to_numpy()   # Convert the contract row (on a single date) into a NumPy array

            result = np.full(len(contracts), np.nan)  # Start with all NaNs (same length as contract list)

            # Slide a rolling window of size `n` across the contract values
            for i in range(len(contracts) - n + 1):
                # Compute dot product between weights and contract window values
                result[i] = np.dot(row[i:i + n], weights) * 100  # Multiply by 100 as per your logic

            # Convert result into a Series with contract names as index
            series = pd.Series(result, index=contracts)

            # Apply outlier filter (you can change the logic inside this function)
            series_filtered = rolling_bounds_filter(series, window=21, k=2)

            # Trim the series to only the front `curve_length` contracts (e.g., first 15 contracts)
            series_trimmed = series_filtered.iloc[:curve_length]

            # Build a DataFrame for this date and structure
            temp_df = pd.DataFrame({
                "Date": date,                             # constant
                "Structure": struct,                      # constant
                "Contract": series_trimmed.index,         # contract names
                "Value": series_trimmed.values            # computed structure values
            })

            struct_data.append(temp_df)  # Append this day's result to list

        # Concatenate all dates for one structure into a single DataFrame
        all_frames.append(pd.concat(struct_data))

    # Concatenate all structures into final long-form DataFrame
    final_df = pd.concat(all_frames)
    # Set MultiIndex (Date, Structure, Contract) and return
    return final_df.set_index(["Date", "Structure", "Contract"])


def compute_percentile_df(str_data_3d):
    latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
    latest_df = str_data_3d.loc[(latest_date)]
    percentile_rank_df = {}
    for (structure, contract), row in latest_df.iterrows():
        try:
            # full series for this (structure, contract) over time
            series = str_data_3d.xs((structure, contract), level=("Structure", "Contract"))["Value"].dropna()
            if series.empty:
                percentile= None

            latest_value = row["Value"]
            # print(series.head())
            # print(latest_value)
            if pd.isna(latest_value):
                return None
            else:
                percentile = percentileofscore(series, latest_value, kind="mean")
            percentile_rank_df[(structure, contract)] = percentile # store

        except KeyError:
            percentile_rank_df[(structure, contract)] = None  # or np.nan
    
    percentile_rank_df = pd.DataFrame.from_dict( # Step 5: create final DataFrame
        percentile_rank_df, orient='index', columns=['Value']
    )

    percentile_rank_df.index = pd.MultiIndex.from_tuples(
        percentile_rank_df.index, names=["Structure", "Contract"]
    )
    return percentile_rank_df


# percentile_rank_df= compute_percentile_df(str_data_3d)
# print(percentile_rank_df)

def compute_risk_reward_roll_df(latest_df: pd.DataFrame) -> pd.DataFrame:
    risk_reward_dict = {}
    risk_reward_diff_dict = {}
    roll_down_dict= {}
    latest_df.index.names = ["Structure", "Contract"] # Ensure proper index naming
    #print(len(latest_df.index.get_level_values("Structure").unique())) #number of ratios
    conts_ct= len(latest_df.index.get_level_values("Contract").unique()) # number of contracts
    for structure in latest_df.index.get_level_values("Structure").unique():
        structure_df = latest_df.loc[structure] # Extract subset for a structure
        contracts = structure_df.index.tolist()  # Extract contract list in order (assumes already sorted)

        for i, contract in enumerate(contracts):
            curr_val = structure_df.loc[contract]["Value"]  #print(i, curr_val)
            if i == 0:
                risk_reward_dict[(structure, contract)] = None
                risk_reward_diff_dict[(structure, contract)] = None
                roll_down_dict[(structure, contract)] = None
                continue
            
            prev_contract = contracts[i - 1]
            prev_val = structure_df.loc[prev_contract]["Value"]

            if pd.isna(curr_val) or pd.isna(prev_val): # Handle divide-by-zero, missing values
                rr = None
                rrdiff= None
                roll_dn= None

            if i== conts_ct-1:
                risk_reward_dict[(structure, contract)] = None
                risk_reward_diff_dict[(structure, contract)] = None
                roll_down_dict[(structure, contract)] = curr_val- prev_val
                continue

            next_contract = contracts[i + 1]
            next_val = structure_df.loc[next_contract]["Value"]

    
            if pd.isna(next_val):
                rr = None
                rrdiff= None
                roll_dn= curr_val= prev_val
            else:
                if curr_val- prev_val== 0: # currently rr accord to long str - if mag<1 then can be displayed in 1/rr form with red fill
                    rr = 98 if next_val > curr_val else -98 if next_val < curr_val else 0
                else:
                    rr= (next_val- curr_val)/  (curr_val- prev_val)
                rrdiff= (next_val- curr_val) - (curr_val- prev_val)  #concavity f(i−1)+ f(i+1)− 2f(i) # if negative- maxima  if positive then minima
                roll_dn= curr_val- prev_val

            # final adjustment            
            rr = max(-98, min(98, rr)) # which are tending to infinity
            if rr<0:
                if rrdiff< 0: #maxima
                    rr= 99 
                elif rrdiff> 0: #minima
                    rr= -99
            risk_reward_dict[(structure, contract)] = rr
            risk_reward_diff_dict[(structure, contract)] = rrdiff
            roll_down_dict[(structure, contract)] = roll_dn

    # Convert to DataFrame with same shape and index as latest_df
    risk_reward_df = pd.DataFrame.from_dict(
        risk_reward_dict, orient="index", columns=["Value"]
    )
    risk_reward_df.index = pd.MultiIndex.from_tuples(
        risk_reward_df.index, names=["Structure", "Contract"]
    )

    # Convert to DataFrame with same shape and index as latest_df
    risk_reward_diff_df = pd.DataFrame.from_dict(
        risk_reward_diff_dict, orient="index", columns=["Value"]
    )
    risk_reward_diff_df.index = pd.MultiIndex.from_tuples(
        risk_reward_diff_df.index, names=["Structure", "Contract"]
    )

    # Convert to DataFrame with same shape and index as latest_df
    roll_down_df = pd.DataFrame.from_dict(
        roll_down_dict, orient="index", columns=["Value"]
    )
    roll_down_df.index = pd.MultiIndex.from_tuples(
        roll_down_df.index, names=["Structure", "Contract"]
    )

    return risk_reward_df, risk_reward_diff_df, roll_down_df





# str_data_3d= compute_3d_structure(out_df, structure_names, local_win=21, curve_length=15)
# latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
# latest_df = str_data_3d.loc[(latest_date)]
# risk_reward_df, risk_reward_diff_df, roll_down_df = compute_risk_reward_roll_df(latest_df)
# percentile_rank_df= compute_percentile_df(str_data_3d)
# print(percentile_rank_df)



#################################visualisation ####################################################################
# # Count them
# dates = str_data_3d.index.get_level_values("Date").unique()
# structures = str_data_3d.index.get_level_values("Structure").unique()
# contracts = str_data_3d.index.get_level_values("Contract").unique()
# print(dates)
# print("latest date", dates[0])
# print(structures)
# print(contracts)
# print("Number of Dates:", len(dates))  # along Z
# print("Number of Structures:", len(structures)) # along Y
# print("Number of Contracts:", len(contracts)) # along x
# print("latest_df", str_data_3d.loc[(latest_date)]
# #accessing 
# # str_data_3d.loc["2024-06-01"] # at any date
# # str_data_3d.loc[("2024-06-01", "L6")] # a structure at any date
# # str_data_3d.loc[("2024-06-01", "L6", "EDU5")] # a specific contrat structure at aspecific date
# # str_data_3d.xs("L6", level="Structure") # 
# # str_data_3d.xs("EDU5", level="Contract") # 



#printnable
# Ensure index is proper MultiIndex
# latest_df.index = pd.MultiIndex.from_tuples(latest_df.index, names=["Structure", "Contract"])
# percentile_rank_df.index = pd.MultiIndex.from_tuples(percentile_rank_df.index, names=["Structure", "Contract"])

# # Pivot to 2D
# latest_2d = latest_df["Value"].unstack("Structure")
# percentile_2d = percentile_rank_df["Percentile"].unstack("Structure")

###########################################################################################################

def generate_heatmap(rounding, layer_df): #initial value populating
    structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
    contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

    # 2. Convert MultiIndex Series to 2D DataFrame
    df_2d = layer_df.unstack(level=0)['Value']
    df_2d = df_2d.reindex(index=contract_order, columns=structure_order)

    # 3. Prepare axes labels and data matrix
    x_labels = df_2d.columns.tolist()              # Structures (x-axis)
    y_labels = df_2d.index.tolist()[::-1]          # Contracts (y-axis, reversed)
    z = df_2d.values[::-1]                        # Matrix (rows reversed)

    # 5. Plot using Plotly (no side color panel)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_labels,
            y=y_labels,
            colorscale='Viridis',
            showscale=False     # Hides the side color panel
            
        )
    )
    fig.update_layout(
        # height=500,
        xaxis=dict(side='top'), 
        height=800,
        margin=dict(l=5, r=5, t=5, b=5),
    )

    # 4. annotation text for each cell
    text = [[f"{val:.{rounding}f}" if not np.isnan(val) else "" for val in row] for row in z]
    fig.update_traces(
        text=text,
        texttemplate="%{text}",
        hovertemplate="Structure: %{x}<br>Contract: %{y}<br>Value: %{z}<extra></extra>"
    )
    return fig

