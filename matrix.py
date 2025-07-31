from str_cal import  rolling_bounds_filter,fill_missing_values,load_data, index, get_ratio, rolling_iqr_filter
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from scipy.stats import percentileofscore
from dash import dcc, html
from kde_help import get_rank
from str_cal import process_series


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
#structure_names= {"D12"}
structure_names= index

def handle_outliers(series: pd.Series, window_size: int, threshold: float, method: str = 'replace') -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError("Input 'series' must be a pandas.Series.")
        
    # --- Step 1: Calculate rolling statistics for the PRECEDING window ---
    
    # Rolling median of the window *before* each point
    # We use shift(1) to ensure each point is compared against the stats of the window that came before it.
    rolling_median = series.rolling(window=window_size, min_periods=3, center=False).median().shift(1)

    # Rolling MAD (Median Absolute Deviation)
    def mad(window):
        median = np.median(window)
        return np.median(np.abs(window - median))

    # .apply() is used here as pandas has no built-in rolling mad
    rolling_mad = series.rolling(window=window_size, min_periods=1, center=False).apply(mad, raw=True).shift(1)
    
    # --- Step 2: Calculate the modified Z-score for each point ---
    
    # The constant 1.4826 scales MAD to be comparable to standard deviation
    # We handle cases where rolling_mad is 0 to avoid division by zero errors
    with np.errstate(divide='ignore', invalid='ignore'):
        score = np.abs(series - rolling_median) / (1.4826 * rolling_mad)
    
    # If rolling_mad was 0, the score is NaN/inf. We can treat these as non-outliers (score=0)
    # as a zero-deviation window means the point should be identical to the median.
    score.fillna(0, inplace=True)
    
    # --- Step 3: Identify outliers based on the score and threshold ---
    is_outlier = score > threshold
    
    # --- Step 4: Handle the outliers based on the chosen method ---
    if method == 'replace':
        series_cleaned = series.copy()
        # Replace outliers with the median of the preceding window
        series_cleaned[is_outlier] = rolling_median[is_outlier]
        return series_cleaned
        
    elif method == 'identify':
        return is_outlier
        
    elif method == 'remove':
        return series[~is_outlier]
        
    else:
        raise ValueError("Method must be one of 'replace', 'identify', or 'remove'.")



def compute_3d_structure(out_df: pd.DataFrame, structure_names= structure_names , local_win=21, curve_length=15 ) -> pd.DataFrame:
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
        for date in dates:  # Loop over each date in the rolling window
            row = out_df.loc[date]
            row = handle_outliers(series=row, window_size=10, threshold=3.0, method='replace')
            row= row.to_numpy() # Convert the contract row (on a single date) into a NumPy array
            result = np.full(len(contracts), np.nan)  # Start with all NaNs (same length as contract list
            for i in range(len(contracts) - n + 1):  # Slide a rolling window of size `n` across the contract values
                # Compute dot product between weights and contract window values
                result[i] = np.dot(row[i:i + n], weights) * 100  # Multiply by 100 as per your logic
            series = pd.Series(result, index=contracts) # Convert result into a Series with contract names as index
            #series_filtered= rolling_iqr_filter(series, window=21, k=2)
            #print( date, struct, series)
            series_filtered = handle_outliers(series=series, window_size=10, threshold=3.0, method='replace')
            # 
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
            if rr is not None:
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

###################################### heatmap values populating #####################################################################
custom_colorscale = [
    [0.0,  'rgb(150, 190, 255)'],  # Strong Light Blue for 0%
    [0.05, 'rgb(170, 205, 255)'],  # Distinctly lighter for 5%
    [0.10, 'rgb(190, 220, 255)'],  # Clearly lighter for 10%
    [0.20, 'rgb(215, 235, 255)'],  # Very light blue for 20%

    # --- Middle Section (Low-distinction area) ---
    # The color changes very little here, as requested.
    [0.5,  'rgb(240, 245, 240)'],  # A neutral, pale green-white for the midpoint

    # --- Green Extreme (High-distinction area) ---
    [0.80, 'rgb(215, 245, 215)'],  # Very light green for 80%
    [0.90, 'rgb(190, 235, 190)'],  # Clearly darker for 90%
    [0.95, 'rgb(170, 225, 170)'],  # Distinctly darker for 95%
    [1.0,  'rgb(150, 215, 150)']   # Strong Light Green for 100%
]



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
            colorscale = custom_colorscale,
            showscale=False     # Hides the side color panel
            
        )
    )
    fig.update_layout(
        # height=500,
        plot_bgcolor='lightgray',  # inside axes
        xaxis=dict(side='top', showgrid=False, tickfont=dict(size=14, family="Orbitron", color="black")),
        yaxis=dict(side='top',showgrid= False, tickfont=dict(size=14, family="Orbitron", color="black")),
        height=800,
        margin=dict(l=5, r=5, t=5, b=5),
    )
    x_coordinate_for_line= {0.5, 3.5, 13.5, 23.5, 27.5}
    for x_line in x_coordinate_for_line:
        if x_line < len(x_labels)-1:
            fig.add_vline(
                x=x_line,
                line_width=1.5,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )


   

    y_coordinate_for_line= {4.5, 8.5, 12.5, 16.5, 20.5, 24.5, 28.5}
    for y_line in y_coordinate_for_line:
        if y_line < len(y_labels)-1:
            fig.add_hline(
                y= len(y_labels)-y_line,
                line_width=1.5,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )
    
    vline_segments = [
        (-0.5, 3.5, 'grey'),
        (3.5, 7.5, 'red'),
        (7.5, 11.5, 'green'),
        (11.5, 15.5, 'blue'),
        (15.5, 19.5, 'gold'),
        (19.5, 23.5, 'purple'),
        (23.5, 27.5, 'orange'),
        (27.5, 31.5, 'pink'),
    ]
    # Add each segment as a separate shape at x = 0
    y_max = len(y_labels) - 1
    for y0, y1, color in vline_segments:
        yf = min(y1, y_max + 0.5)  # allow up to the midpoint after last y-label
        if y0 > y_max + 0.5:
            break
        fig.add_shape(
            type='line',
            x0= -0.5, x1= -0.5,
            y0= y_max - y0,
            y1= y_max - yf,
            line=dict(color=color, width=2.5),
            layer='above'
        )

    # 4. annotation text for each cell
    text = [[f"{val:.{rounding}f}" if not np.isnan(val) else "" for val in row] for row in z]
    fig.update_traces(
        text=text,
        texttemplate="%{text}",
        hovertemplate="<b>%{x} | %{y}</b><br>Val: %{z:.1f} <extra></extra>",
        # textfont=dict(
        #    # size=18,  # Set the font size
        #     family="Orbitron"
        #  )
    )
    return fig


def create_blank_heatmap(layer_df):
    structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
    contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

    empty_z =  z_empty = np.zeros((len(contract_order ), len(structure_order)))
    text_empty = [["" for _ in structure_order] for _ in contract_order ]

    fig = go.Figure(
        data=go.Heatmap(
        z= empty_z,
        x= structure_order,
        y= contract_order,
        text= text_empty,
        #hoverinfo="text",
        hovertemplate="<b>%{x} | %{y}</b><br>Val: %{z:.1f} <extra></extra>",
        colorscale="lightgray",  # Initial dummy
        showscale=False
        )
    )

    fig.update_layout(
        # height=500,
        plot_bgcolor='lightgray',
        xaxis=dict(side='top', showgrid=False, tickfont=dict(size=14, family="Orbitron", color="black")),
        yaxis=dict(side='top', showgrid=False, tickfont=dict(size=14, family="Orbitron", color="black")),
        height=800,
        margin=dict(l=5, r=5, t=5, b=5),
    )
    x_coordinate_for_line= {0.5, 3.5, 13.5, 23.5, 27.5}
    for x_line in x_coordinate_for_line:
        if x_line < len(structure_order)-1:
            fig.add_vline(
                x=x_line,
                line_width=1,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )

    y_coordinate_for_line= {4.5, 8.5, 12.5, 16.5, 20.5, 24.5, 28.5}
    for y_line in y_coordinate_for_line:
         if y_line < len(contract_order)-1:
            fig.add_hline(
                y= len(contract_order)-y_line,
                line_width=1,
                line_dash="solid",
                line_color="white",
                # annotation_text="Key Event", # Optional: add a label to the line
                # annotation_position="top right"
            )
    return fig


################# heatmap coloring  ##############################################################
def color_heatmap(fig, type, layer_df): #initial value populating
    try:
        if not isinstance(layer_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
        contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

        # 2. Convert MultiIndex Series to 2D DataFrame
        df_2d = layer_df.unstack(level=0)['Value']
        df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
        new_z = df_2d.values[::-1]                        # Matrix (rows reversed)

        # 4. Update existing heatmap trace (assumes 1 trace only)
        if fig.data and isinstance(fig.data[0], go.Heatmap):
            fig.data[0].z = new_z  # this controls coloring
            fig.data[0].colorscale = custom_colorscale
            fig.data[0].showscale = False
            fig.data[0].hoverinfo = 'skip'
        ###If you want to style cells (e.g. bold outline or highlight based on a condition), you’ll need to use go.Heatmap + shapes or overlay a Scatter trace
        return fig
    
    # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in  color_heatmap:  {e}")
        return fig # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error in color_heatmap: Missing expected level or column: {e}")
        return fig
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error in color_heatmap occurred: {e}")
        return fig
    


########################## highlighter filter ####################

def filter_grey (fig, type, layer_df): #initial value populating
    try:
        if not isinstance(layer_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = layer_df.index.get_level_values('Structure').unique().tolist()
        contract_order = layer_df.index.get_level_values('Contract').unique().tolist()

        # 2. Convert MultiIndex Series to 2D DataFrame
        df_2d = layer_df.unstack(level=0)['Value']
        df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
        new_z = df_2d.values[::-1]                        # Matrix (rows reversed)

        # Create mask for the condition
        """" Set gray values for cells not meeting condition
        Using None for values that don't meet the condition will make them transparent,
        allowing a background color or another trace to show through if desired.
        If a specific gray color is needed, you would assign a numerical value and
        define that value in your colorscale to map to gray """

        if(type== 595):
            mask = (new_z >= 95) | (new_z <= 5)
        elif(type== 1090):
            mask = (new_z >= 90) | (new_z <= 10)

        colored_z = np.where(mask, new_z, None)
        # 4. Update existing heatmap trace (assumes 1 trace only)
        if fig.data and isinstance(fig.data[0], go.Heatmap):
            fig.data[0].z = colored_z  # this controls coloring
            fig.data[0].showscale = False
            fig.data[0].hoverinfo = 'skip'
        ###If you want to style cells (e.g. bold outline or highlight based on a condition), you’ll need to use go.Heatmap + shapes or overlay a Scatter trace
        return fig

    # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in filter_grey : {e}")
        return fig # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error: Missing expected level or column in filter_grey : {e}")
        return fig
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error occurred in filter_grey: {e}")
        return fig






######################################################## hover t3mplate ##########################3

def hovertemplate_heatmap(heatmap, latest_df, risk_reward_df, risk_reward_diff_df, roll_down_df, percentile_df):
    try:
        if not isinstance(latest_df.index, pd.MultiIndex):
            raise ValueError("Input 'fig' must be a Figure with a Heatmap trace at index 0.")
        structure_order = latest_df.index.get_level_values('Structure').unique().tolist()
        contract_order = latest_df.index.get_level_values('Contract').unique().tolist()
        x_labels = structure_order
        y_labels = contract_order[::-1]

        # 2. Convert MultiIndex Series to 2D DataFrame
        processed_dfs = {}
        source_data_map = {
            'Latest': latest_df,
            'Pct': percentile_df,
            'R/Rd': risk_reward_diff_df,
            'R/R': risk_reward_df,
            'RlDn': roll_down_df,
        }
        for name, df_series in source_data_map.items():
            if isinstance(df_series, pd.DataFrame):
                # If it's a DataFrame with a 'Value' column, select it first.
                df_series = df_series['Value']
            # Unstack the 'Structure' level to become the columns.
            df_2d = df_series.unstack(level='Structure')
            df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
            processed_dfs[name] = df_2d

        # hovertext ##
        hover_text_matrix = []
        for contract in y_labels:
            row_texts = []
            for structure in x_labels:
                cell_info = []
                for name, df in processed_dfs.items():
                    value = df.loc[contract, structure]
                    if pd.notna(value):
                        # Format each factor on a new line
                        cell_info.append(f"{name}: {value:.1f}")

                # Join all factors with an HTML line break
                row_texts.append("<br>".join(cell_info))
            hover_text_matrix.append(row_texts)

        # Reconstruct the Figure object from the dictionary
        heatmap = go.Figure(heatmap)
        heatmap.update_traces(
            selector=dict(type="heatmap"),  # Optional if only one trace
            customdata= hover_text_matrix,
            hovertemplate="<b>%{x} | %{y}</b><br>%{customdata}<extra></extra>"
        )
        return heatmap
    
     # --- Specific Error Handling ---
    except (ValueError, TypeError) as e:
        print(f"Input Validation Error in hovertemplate_heatmap: {e}")
        return heatmap # Return the original figure
    except KeyError as e:
        print(f"Data Structure Error: Missing expected level or column in hovertemplate_heatmap: {e}")
        return heatmap
    # --- General Fallback Error Handling ---
    except Exception as e:
        print(f"An unexpected error occurred  in hovertemplate_heatmap: {e}")
        return heatmap

###################################################### side panel #############################
def get_adjacent_values(str_data_3d,  x_val, y_val): #D3, SFR3
    latest_date = str_data_3d.index.get_level_values("Date").unique()[0]
    latest_df = str_data_3d.loc[latest_date]
    structure_order = latest_df.index.get_level_values('Structure').unique().tolist()
    contract_order = latest_df.index.get_level_values('Contract').unique().tolist()

    df_series = latest_df['Value']
    df_2d = df_series.unstack(level='Structure')
    df_2d = df_2d.reindex(index=contract_order, columns=structure_order)
    
    x_labels = df_2d.columns.tolist()  # S3, l3, L6   
    y_labels = df_2d.index.tolist() # SFR1,SFR2...
    
    try:
        curr_col = x_labels.index(x_val)
        curr_row= y_labels.index(y_val)
        
    except ValueError:
        return None, None
    prev_data, next_data = None, None # we need value in the same column
    if curr_row > 0:
        prev_data = df_2d.iloc[curr_row- 1 , curr_col]
    if curr_row < len(y_labels) - 1:
        next_data = df_2d.iloc[curr_row+ 1,  curr_col]
    # print("cc", curr_col, "cr", curr_row)
    # print("pv", prev_data,"nv", next_data)
    return prev_data, next_data 



def generate_heatmap_detail_panel (clicked_series, x_val, y_val, prev_val, next_val):
    clicked_series = pd.Series(clicked_series.iloc[:, 0].values)
    #print(type(clicked_series), len(clicked_series))
    series= process_series(clicked_series, window=11, k=2)
    # --- Step 1: Create the Sparkline Plot ---
    sparkline_fig = go.Figure(
        go.Scatter(
            x= series.index,
            y= series,
            mode='lines',
            line_shape='spline',
            line=dict(width=2, color='#0d6efd'),
            #fill='tozeroy', 
            fillcolor='rgba(13, 110, 253, 0.2)'
        )
    )
    sparkline_fig.update_layout(
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=4, b=4),
        height=60,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )

    #step 2   Mini Bar Chart: Volatility or Daily Delta View
    barchart_cod_fig = go.Figure(
        go.Bar(
            x=series.index,
            y=series.diff(),
            marker_color=['#28a745' if x > 0 else '#dc3545' for x in series.diff()],
            width=0.8,
        )
    )
    
    barchart_cod_fig.update_layout(
        template='plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=4, b=4),
        height=60,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False, showticklabels=False),
    )

    #other matrics step3 
    latest_val= series.iloc[0]
    rank= get_rank(series, latest_val)
    min_val= series.min()
    max_val= series.max() 
    roll_down= latest_val- prev_val if prev_val is not None else None
    roll_up= latest_val- next_val if next_val is not None else None
    risk_reward_diff= (next_val- latest_val) - (latest_val- prev_val) if prev_val is not None and next_val is not None else None
    risk_reward_ratio = None
    if roll_up is not None and roll_up != 0:
        risk_reward_ratio = roll_down / roll_up if roll_down is not None else None

    std_dev= series.std()
    mean = series.mean()
    median = series.median() 
    range_span = max_val - min_val
    z_score = (latest_val - mean) / std_dev if std_dev != 0 else np.nan

     # --- Step 4: Assemble the Panel's Layout Components ---
    panel_content = dbc.Container([
        # Header Row with Title and Close Button
        dbc.Row([
            dbc.Col(html.H5(f"{x_val} | {y_val}", className="my-auto"), width='auto'),
            dbc.Col(
                html.Span(
                    "×",  # The 'x' character for the button
                    id="details-panel-close-btn",
                    n_clicks=0,
                    className="panel-close-button",  # Custom class for your separate CSS file
                    style={'cursor': 'pointer', 'fontSize': '36px', 'font-weight': 'bold', 'lineHeight': '1'}      # Changes the mouse cursor to a pointer on hover
                ),
            width="auto",
            )
        ], align="center", justify="between", className="mb-3"),

        # Main Value Display and Sparkline
        dbc.Card(dbc.CardBody([
            html.H6("Current Value", className="card-subtitle mb-2 text-muted"),
            html.H3(f"{latest_val:.2f}" if latest_val is not None else "N/A", className="card-title"),
            dcc.Graph(figure=sparkline_fig, config={'displayModeBar': False}, className="mt-2")
        ])),

        # Daily Change Bar Chart
        dbc.Card(dbc.CardBody([
            html.H6("Daily Change", className="card-subtitle mb-2 text-muted"),
            dcc.Graph(figure=barchart_cod_fig, config={'displayModeBar': False})
        ]), className="mt-3"),
        
        # Key Metrics Grid
        html.H6("Statistical Analysis", className="mt-4 mb-2"),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Rank", className="text-muted small mb-0"),
                html.H5(f"{rank:.0f}%" if rank is not None else "N/A")
            ])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Z-Score", className="text-muted small mb-0"),
                html.H5(f"{z_score:.2f}" if z_score is not None else "N/A")
            ])), width=6),
        ], className="g-2"),

        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
            html.P("Min", className="text-muted small mb-0"),
            html.H5(f"{min_val:.1f}" if min_val is not None else "N/A")
        ])), width=6),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Max", className="text-muted small mb-0"),
                html.H5(f'{max_val:.1f}' if max_val is not None else "N/A")
            ])), width=6),
        ], className="g-2 mt-2"),

        dbc.Row([
             dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Roll Dn", className="text-muted small mb-0"),
                html.H5(f"{roll_down:.1f}" if roll_down is not None else "N/A")
            ])), width=6),
            
            dbc.Col(dbc.Card(dbc.CardBody([
                html.P("Roll Up", className="text-muted small mb-0"),
                html.H5(f"{roll_up:.1f}" if roll_up is not None else "N/A")
            ])), width=6),
        ], className="g-2 mt-2"),

     

        # Roll and Risk/Reward Analysis
        html.H6("Roll & Risk Analysis", className="mt-4 mb-2"), 
        dbc.ListGroup([
            # dbc.ListGroupItem([html.Span("Roll Down", className="fw"), html.Span(f"{roll_down:.1f}" if roll_down is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Std Dev", className="fw"), html.Span(f"{std_dev:.1f}" if std_dev is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Median", className="fw"), html.Span(f"{median:.1f}" if median is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Mean", className="fw"), html.Span(f"{mean:.1f}" if mean is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Risk/Reward Diff", className="fw"), html.Span(f"{risk_reward_diff:.1f}" if risk_reward_diff is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Risk/Reward Ratio", className="fw"), html.Span(f"{risk_reward_ratio:.1f}" if risk_reward_ratio is not None else "N/A", className="float-end")]),
            dbc.ListGroupItem([html.Span("Range Span", className="fw"), html.Span(f"{range_span:.1f}" if range_span is not None else "N/A", className="float-end")]),
            # dbc.ListGroupItem([html.Span("Max Value", className="fw"), html.Span(f"{max_val:.2f}" if max_val is not None else "N/A", className="float-end")]),
            # dbc.ListGroupItem([html.Span("Min Value", className="fw"), html.Span(f"{min_val:.2f}" if min_val is not None else "N/A", className="float-end")]),
            
        ], flush=True),

    ], fluid=True, style={'padding': '1rem'})
    
    return panel_content



    

