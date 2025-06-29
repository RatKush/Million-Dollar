# """"----------------------------------intact---------------------------------------"""
# from main_help import load_data, fill_missing_values
# from str_cal import get_ratio, calculate_str, remove_outliers

# str_name= "D3(II)"  
# out_curve_df = fill_missing_values(load_data())                                              ## 2. input ##
# str_df = calculate_str(out_curve_df, get_ratio(str_name))
# str_df = remove_outliers(str_df,lower_quantile=0.01, upper_quantile=0.99)

# curve_length= 15                                        ## 1. trim upto req str 
# str_df= str_df.iloc[:,:curve_length]                              

# """"  ----------------------------intact--------------------------------------------"""
import pandas as pd

def row_logic_for_eases_hikes(row, check_window=4, max_cols=8):
    values = row.values[:max_cols]
    init_sum = sum(values[:check_window])
    total = 0
    if init_sum >= 0:                       # We're summing positive values, until a negative appears (except at index 0)
        for i, val in enumerate(values):
            if val < 0 and i != 0:
                break
            total += val
    else:                                   # We're summing negative values, until a positive appears (except at index 0)
        for i, val in enumerate(values):
            if val > 0 and i != 0:
                break
            total += val

    return total


row1= [1,2,3,4,5,6,7,8,9,10]  #36
row2= [-1,-2,-3,-4,-5,-6,-7,-8,-9,-10] #-36
row3= [-1,0,1,2,3,4,5,6,7,8] #20
row4= [1,0,-1,-2,-3,-4,-5,-6,-7,-8] # -20
row5= [1,2,3,4,5] #15
row6= [-1,-2,-3,-4,-5] #-15
row7= [-1,0,1,2,3] #5
row8= [1,0,-1,-2,-3] #-5

print(row_logic_for_eases_hikes(pd.Series(row1), 8))
print(row_logic_for_eases_hikes(pd.Series(row2), 8))
print(row_logic_for_eases_hikes(pd.Series(row3), 8))
print(row_logic_for_eases_hikes(pd.Series(row4), 8))

print(row_logic_for_eases_hikes(pd.Series(row5), 8))
print(row_logic_for_eases_hikes(pd.Series(row6), 8))
print(row_logic_for_eases_hikes(pd.Series(row7), 8))
print(row_logic_for_eases_hikes(pd.Series(row8), 8))