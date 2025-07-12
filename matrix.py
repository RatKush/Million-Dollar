from str_cal import  rolling_bounds_filter,fill_missing_values,load_data, index, get_ratio,_rolling_sumproduct
import pandas as pd
import numpy as np

local_win=21
filepath= "SR3.xlsx"
curve_length= 15

out_df = fill_missing_values(load_data(local_win, filepath ))
print(out_df.shape)
structure_names= index
str_data_3d= {}
for struct in structure_names:
    struct_vals = []

    ratio= get_ratio(struct)
    for i in range(out_df.shape[0]):
        
        print(out_df.iloc[i]) #row
        for j in range(out_df.shape[1]):
            print(out_df.iloc[:,j])
            col= out_df.iloc[j]
            r= _rolling_sumproduct(col, ratio)