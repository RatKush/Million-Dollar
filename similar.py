import time
from typing import Optional, Union, Dict, Any
import pandas as pd
import logging
from str_cal import process_raw_data, serialize_dataframe, process_structure_data



DEFAULT_FILES = ["SR3_ED_GEN.xlsm", "SR3.xlsx"]
comdty = "SR3"
win_local= 21
DEFAULT_LOOKBACK = 250
str_name= "L6"
def extract_raw_data(filename: str, lookback_prd: Union[str, int]) -> Dict[str, Any]:
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
    
        try:
            ts = pd.to_datetime(raw_df.index[0], errors='coerce')
            latest_date = ts.strftime("%d-%m-%y") if pd.notnull(ts) else None
        except Exception as e:
            logging.warning(f"Could not parse latest date: {e}")
            latest_date = None

        return raw_df, latest_date
        
    except Exception as e:
        logging.error(f"Error in extract_raw_data_callback for file {filename}: {e}")
        return {}, None

df_raw_data, latest_date = extract_raw_data(DEFAULT_FILES[0], DEFAULT_LOOKBACK)

#structure calculation
str_df = process_structure_data(df_raw_data, comdty, win_local ,str_name)


"""
SOFR PCA + HMM + Monte-Carlo 5-day curve predictor (single-file)
Author: (you)
Purpose:
 - Take an already-loaded DataFrame `df` of daily settlement values:
     index -> dates (datetime index, latest date last or first; code will handle)
     columns -> structure names (e.g., 'SFR1', 'SFR2', 'SFR3', ... )
     values -> daily settlement prices (floats; NaNs allowed)
 - Compute PCA on standardized series (on *values* or *returns* depending on CONTROL)
 - Fit HMM on PCA scores
 - Use HMM emission & transition matrices to Monte-Carlo simulate many possible PCA-score
   paths over next HORIZON days, reconstruct full-curve outcomes, produce distributions
 - For each structure compute:
     * expected T+H mean (absolute and delta vs today)
     * P(Δ > +3σ_5d) and P(Δ < -3σ_5d) (empirical from sims)
     * recommended action using explicit thresholds
 - Print a clear daily summary and region-level statistics.
 - NO data loader built (script expects `df` to be present). See the small optional
   conversion snippet below if you actually have `df_raw_data` dict and want to convert it.

Design choices & notes:
 - We run PCA on *standardized column values* by default (center & scale). Optionally you can
   run PCA on returns or vol-normalized changes by changing CONTROL PCA_ON_RETURNS.
 - HMM uses Gaussian emissions on PCA scores (multivariate). Use full covariance for realism.
 - Monte-Carlo sim uses state-path sampling (simulates regimes day by day) and daily emissions;
   final-day PCA score is used to reconstruct full-curve via PCA inverse and scaler inverse.
 - All thresholds (N_SIMS, PROB_THRESHOLD, SIGMA_MULT, etc.) are in the CONTROLS section.
 - The code prints summary top/bottom lists and a full DataFrame (first N rows).
 - Keep an eye on runtime for N_SIMS (10k sims × ~K=3 PCs × M structures is usually fine).
"""

# -------------------------
# CONTROLS (tune these)
# -------------------------
INPUT_ASSUMPTION = "df_raw_data"     # "df" means code expects a pandas DataFrame variable named `df`.
                            # If you set to "df_raw_dict", see the optional snippet below (commented)
N_PCS = 3                   # number of principal components to keep #3 PCs usually explain 96–99% of movement in SOFR curve.
N_STATES = 3                # number of HMM regimes Hidden Markov Model states #3 is common: Regime 0: stable Regime 1: rallying / cutting Regime 2: sell-off / hiking
N_SIMS = 10000              # Monte Carlo simulations (10k recommended) - for more accusracy can be increased to 25K or 50K if runtime acceptable
HORIZON = 5                 # days ahead to forecast
RANDOM_SEED = 42
SIGMA_MULT = 3.0            # 3-sigma threshold multiplier for extreme moves
PROB_THRESHOLD = 0.65       # prob threshold for 'Strong Long/Short' label
Z_RESIDUAL_THRESHOLD = 1.3  # PCA residual z threshold for cheap/rich tagging
PCA_ON_RETURNS = False      # If True: run PCA on daily first differences; if False: on levels
VERBOSE = True
NUM_CONT_COLUMNS = 12      # number of columns from df to use (from left); adjust as needed
REGION_MAPPING = {          # edit to your actual column names or integer indices
    'front': ['SFR1', 'SFR2', 'SFR3',  'SFR4'],            # example: ['SFR1','SFR2']
    'belly': ['SFR5','SFR6' , 'SFR7', 'SFR8'],
    'long': ['SFR9','SFR10' , 'SFR11', 'SFR12']
}

# -------------------------

# -------------------------
# Imports
# -------------------------
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.stats import norm
from hmmlearn.hmm import GaussianHMM
import time
import warnings
warnings.filterwarnings('ignore')
np.random.seed(RANDOM_SEED)

# -------------------------
# OPTIONAL: convert df_raw_data dict -> df (UNCOMMENT if needed)
# -------------------------
# If you only have `df_raw_data` (the dict printed earlier), you can convert it to df with:
# (This is optional and commented to satisfy your request of 'no loader'.)
#
# if INPUT_ASSUMPTION == "df_raw_dict" and 'df_raw_data' in globals():
#     raw = globals()['df_raw_data']
#     data = raw.get('data')
#     cols = raw.get('columns')
#     idx = raw.get('index')
#     df = pd.DataFrame(data, index=pd.to_datetime(idx), columns=cols)
#     df.index = pd.to_datetime(df.index)
#     df = df.sort_index()   # oldest->newest
#
# NOTE: Keep this commented if you will provide `df` yourself.

# -------------------------
# Sanity check: 'df' must exist
# -------------------------
if 'str_df' not in globals():
    raise RuntimeError("DataFrame `df` not found in environment. Provide a pandas DataFrame `df` and re-run.")

# copy user df so we don't mutate original
df_in = str_df.iloc[:,:NUM_CONT_COLUMNS].copy()

# -------------------------
# Align index & ensure datetime
# -------------------------
# Accept either latest-first or latest-last. We will standardize to ascending order (oldest -> newest)
try:
    df_in.index = pd.to_datetime(df_in.index)
except Exception:
    # If conversion fails raise
    raise RuntimeError("Unable to parse df.index as datetimes. Fix the index and retry.")

# Drop columns with all NaN and rows with all NaN
df_in = df_in.dropna(axis=1, how='all').dropna(how='all', axis=0)

# Sort ascending so oldest -> newest; we will use last row as 'latest'
df_in = df_in.sort_index(ascending=True) 

print(df_in.head())
if VERBOSE:
    print("Data loaded. Shape:", df_in.shape)
    print("Latest date (data last row):", df_in.index[-1].strftime("%d-%m-%y"))
    print("Column sample:", df_in.columns[:NUM_CONT_COLUMNS].tolist())

# -------------------------
# Preprocess: numeric conversion & light gap handling
# -------------------------
# Convert all to numeric, coerce errors to NaN
df_in = df_in.apply(pd.to_numeric, errors='coerce')

# If small gaps exist, forward-fill then backfill; large gaps left as NaN
df_proc = df_in.ffill(limit=5).bfill(limit=5)

# Final check for empty or too small dataset
if df_proc.shape[0] < 20 or df_proc.shape[1] < 3:
    raise RuntimeError(f"Insufficient data after preprocessing: rows={df_proc.shape[0]} cols={df_proc.shape[1]}")

# -------------------------
# Choose PCA basis: levels or returns
# -------------------------
if PCA_ON_RETURNS:
    X = df_proc.diff().dropna()         # daily changes
    if VERBOSE:
        print("PCA on returns selected. Input shape:", X.shape)
else:
    X = df_proc.copy()                  # levels
    if VERBOSE:
        print("PCA on levels selected. Input shape:", X.shape)

# -------------------------
# Standardize (center & scale) per column, but keep scaler for inverse mapping
# -------------------------
scaler = StandardScaler(with_mean=True, with_std=True) # Z = (x - mean) / std
Xs = scaler.fit_transform(X.values)   # shape (T, M)

# -------------------------
# PCA: fit and get scores (factor time series)
# -------------------------
pca = PCA(n_components=N_PCS)
scores = pca.fit_transform(Xs)        # shape (T, K)
explained = pca.explained_variance_ratio_
if VERBOSE:
    print(f"PCA fitted: top {N_PCS} explain {explained.sum():.3f} of variance") # usually sum >95% with 3 PCs 
    print("Explained variance ratio per PC:") # If explained variance is <70% → your data might be noisy, If PC1 alone explains >95% → too few structures or wrong preprocessing , If PC2 or PC3 are tiny (<1%) → you might not have enough tenor points
    for i, v in enumerate(explained, 1):
        print(f"  PC{i}: {v:.3f}")

# Put scores into DataFrame aligning with X.index
idx = X.index
pc_cols = [f"PC{i+1}" for i in range(N_PCS)]
df_scores = pd.DataFrame(scores, index=idx, columns=pc_cols)

# -------------------------
# HMM: fit Gaussian HMM on PCA scores (multivariate emissions)
# -------------------------
# We fit on the historical scores (dropna not needed if preprocessing ok)
hmm = GaussianHMM(n_components=N_STATES, covariance_type='full', n_iter=300, random_state=RANDOM_SEED)
hmm.fit(df_scores.values)   # EM fit; produces .means_ (n_states x K) and .covars_ (n_states x K x K) and .transmat_

# Posterior probabilities (filtered/smoothed) for each date (shape T x n_states)
logprob, posteriors = hmm.score_samples(df_scores.values)
# Use last row as today's smoothed filtered probs
alpha_t = posteriors[-1, :]   # vector length n_states

if VERBOSE:
    print("HMM fitted. Transition matrix:")
    print(np.round(hmm.transmat_, 3))
    print("Last-day regime probabilities (filtered):", np.round(alpha_t, 4))

# -------------------------
# Compute empirical 5-day sigma per structure (used for 3σ thresholds)
# -------------------------
# Using historical differences with same horizon (non-overlapping or overlapping?) -> use overlapping diff
delta_h = df_proc.diff(periods=HORIZON).dropna()
sigma_5 = delta_h.std(axis=0).values   # shape (M,)  (units: same as df values)
if VERBOSE:
    print("Computed empirical 5-day sigma for each structure.")

# -------------------------
# Prepare inputs for Monte Carlo
# -------------------------
# We'll simulate paths of PCA scores using HMM regimes and emissions then map to structure space.
n_states = N_STATES
K = N_PCS
M = df_proc.shape[1]
cols = df_proc.columns.tolist()

# HMM emission params
mus = hmm.means_                      # (n_states, K)
covs = hmm.covars_                    # (n_states, K, K)

transmat = hmm.transmat_              # (n_states, n_states)
# Precompute cumulative transition rows for sampling
trans_cum = np.cumsum(transmat, axis=1)

# Last observed PCA score (most recent)
s_last = df_scores.values[-1, :]      # shape (K,)
# Last raw structure (most recent)
x_last = df_proc.values[-1, :]        # shape (M,)

# PCA inverse mapping helpers:
# pca.components_ shape: (K, M) if scikit-learn stores components_ as (n_components, n_features)
# Note: pca.inverse_transform expects array in component space and returns standardized-space vector
# Then scaler.inverse_transform will map standardized->raw units
# We will use pca.inverse_transform(...) then scaler.inverse_transform(...)
# Confirm dims:
#   If we have score vector s of length K: pca.inverse_transform(s.reshape(1,-1)) -> standardized vector length M
#   scaler.inverse_transform(that) -> raw vector length M

# -------------------------
# Monte Carlo simulation of HORIZON-day ahead scenarios
# -------------------------
def run_monte_carlo(n_sims=N_SIMS, horizon=HORIZON, seed=RANDOM_SEED, alpha_t=alpha_t):
    """
    Simulate n_sims end-of-horizon structure outcomes.
    Algorithm:
      - For each sim:
          * sample S_{t+1} based on alpha_t @ transmat
          * simulate regime path S_{t+1},...,S_{t+H} via multinomial draws using transmat
          * for each day u in 1..H: draw PCA score s_u ~ N(mu_{S_u}, cov_{S_u})
          * keep last s_H, invert PCA -> standardized X -> raw X
      - Return sims array shape (n_sims, M) of x_{t+H} values
    """
    np.random.seed(seed)
    sims = np.zeros((n_sims, M), dtype=float)

    # Precompute initial next-state probs vector
    initial_next_state_probs = alpha_t @ transmat   # shape (n_states,)
    init_cum = np.cumsum(initial_next_state_probs)

    for sim in range(n_sims):
        # sample S_{t+1}
        r = np.random.rand()
        s = int(np.searchsorted(init_cum, r))
        # state path
        states = [s]
        for h in range(1, horizon):
            r = np.random.rand()
            s = int(np.searchsorted(trans_cum[s], r))
            states.append(s)

        # simulate emissions along path; we only ultimately need s_last_h (the last day's score),
        # but sampling all days respects path randomness if you want path-dependent returns in future.
        for state in states:
            # draw score vector
            # Use np.random.multivariate_normal with mean mus[state], cov covs[state]
            score_draw = np.random.multivariate_normal(mean=mus[state], cov=covs[state])
        s_h = score_draw  # final day score vector (K,)

        # transform back to raw structure units
        standardized_sim = pca.inverse_transform(s_h.reshape(1, -1))  # shape (1, M)
        raw_sim = scaler.inverse_transform(standardized_sim)[0]      # shape (M,)
        sims[sim, :] = raw_sim

        # small progress print
        if VERBOSE and (sim + 1) % max(1, (n_sims // 5)) == 0 and sim > 0:
            print(f"  MonteCarlo: {sim+1}/{n_sims} sims done")

    return sims

# run MC
t0 = time.time()
sims = run_monte_carlo(n_sims=N_SIMS, horizon=HORIZON, seed=RANDOM_SEED, alpha_t=alpha_t)
t1 = time.time()
if VERBOSE:
    print(f"Monte Carlo done: {N_SIMS} sims in {t1-t0:.1f}s")

# -------------------------
# Analyze simulation outcomes
# -------------------------
# delta simulations (Δ = x_{t+H} - x_t)
delta_sims = sims - x_last.reshape(1, -1)     # shape (n_sims, M)

# Per-structure stats
mean_delta = delta_sims.mean(axis=0)
median_delta = np.median(delta_sims, axis=0)
std_delta = delta_sims.std(axis=0)

# threshold for extreme events
thr = SIGMA_MULT * sigma_5   # shape (M,)

# probabilities
p_gt_pos = (delta_sims > thr.reshape(1, -1)).mean(axis=0)   # P(Δ > +3σ)
p_lt_neg = (delta_sims < (-thr).reshape(1, -1)).mean(axis=0) # P(Δ < -3σ)

# PCA implied fair-values and residuals (today)
# To compute PCA implied values for today we invert today's scores
reconstructed_std_all = pca.inverse_transform(df_scores.values)  # standardized-space matrix (T, M)
reconstructed_raw_all = scaler.inverse_transform(reconstructed_std_all)  # raw units (T, M)
residuals_all = df_proc.values - reconstructed_raw_all  # (T, M)
# last residual for each structure:
last_resid = residuals_all[-1, :]
resid_mean = residuals_all.mean(axis=0)
resid_std = residuals_all.std(axis=0)
z_resid = (last_resid - resid_mean) / (resid_std + 1e-12)

# Build summary DataFrame for printing
summary = pd.DataFrame({
    'structure': cols,
    'latest': x_last,
    'mean_delta': mean_delta,
    'median_delta': median_delta,
    'std_delta_sim': std_delta,
    f'p_gt_+{int(SIGMA_MULT)}sigma': p_gt_pos,
    f'p_lt_-{int(SIGMA_MULT)}sigma': p_lt_neg,
    '5d_sigma_empirical': sigma_5,
    'z_resid': z_resid
})
# recommended action logic (explicit)
def pick_action(row):
    p_up = row[f'p_gt_+{int(SIGMA_MULT)}sigma']
    p_dn = row[f'p_lt_-{int(SIGMA_MULT)}sigma']
    zr = row['z_resid']
    if p_up >= PROB_THRESHOLD and zr < -Z_RESIDUAL_THRESHOLD:
        return 'Strong Long'
    if p_dn >= PROB_THRESHOLD and zr > Z_RESIDUAL_THRESHOLD:
        return 'Strong Short'
    if p_up >= PROB_THRESHOLD:
        return 'Long (prob)'
    if p_dn >= PROB_THRESHOLD:
        return 'Short (prob)'
    # otherwise check small signals
    if zr <= -Z_RESIDUAL_THRESHOLD:
        return 'Buy (resid cheap)'
    if zr >= Z_RESIDUAL_THRESHOLD:
        return 'Sell (resid rich)'
    return 'No Trade / Watch'

summary['action'] = summary.apply(pick_action, axis=1)

# Add percentiles of delta distribution for context
q10 = np.percentile(delta_sims, 10, axis=0)
q90 = np.percentile(delta_sims, 90, axis=0)
summary['delta_q10'] = q10
summary['delta_q90'] = q90

# Sort summary for display: by absolute mean_delta desc
summary['abs_mean'] = np.abs(summary['mean_delta'])
summary_sorted = summary.sort_values('abs_mean', ascending=False).reset_index(drop=True)

# -------------------------
# Region-level statistics
# -------------------------
region_stats = {}
for region_name, mapping in REGION_MAPPING.items():
    if not mapping:
        region_stats[region_name] = {'note': 'no columns mapped'}
        continue
    # support both index ints and column names
    if all(isinstance(x, int) for x in mapping):
        idxs = mapping
    else:
        idxs = [cols.index(c) for c in mapping]
    region_delta = delta_sims[:, idxs].mean(axis=1)
    mu = region_delta.mean()
    sd = region_delta.std()
    p_up = (region_delta > SIGMA_MULT * sd).mean()
    p_dn = (region_delta < -SIGMA_MULT * sd).mean()
    region_stats[region_name] = {
        'mean_delta': mu,
        'std_delta': sd,
        f'p_gt_+{int(SIGMA_MULT)}sigma': p_up,
        f'p_lt_-{int(SIGMA_MULT)}sigma': p_dn
    }

# -------------------------
# Print outputs (no CSV)
# -------------------------
pd.set_option('display.float_format', lambda x: f"{x:0.6f}")
print("\n===== PCA + HMM 5-day forecast summary =====")
print(f"Data last date: {df_proc.index[-1].strftime('%d-%m-%y')}")
print(f"Forecast horizon: {HORIZON} days, MonteCarlo sims: {N_SIMS}")
print("\nTop structures by predicted absolute move (mean):")
print(summary_sorted[['structure','latest','mean_delta','delta_q10','delta_q90','p_gt_+3sigma','p_lt_-3sigma','z_resid','action']].head(12))

print("\nFull summary (first 30 rows):")
print(summary_sorted.head(30).to_string(index=False))

print("\nRegion stats:")
for k,v in region_stats.items():
    print(k, v)

print("\nHMM Transition Matrix (rounded):")
print(np.round(transmat,3))
print("\nHMM State Means (PC-space):")
for i in range(n_states):
    print(f"State {i}: mean={np.round(mus[i],4)} cov_diag={np.round(np.diag(covs[i]),6)}")

print("\nDone.")

# -------------------------
# End of script
# -------------------------

