"""
FireFusion — TCN Classifier Training Pipeline
==============================================
Location : src/training/train_classifier.py

Full training workflow:
    1. Load ERA5-Land env CSV and satellite fire CSV
    2. Spatially join fire detections to ERA5 grid cells
    3. Build complete label table (env data as spine, fire as labels)
    4. Time-based train / val / test split (no leakage)
    5. Fit StandardScaler on training data only
    6. Build FireDataset with on-the-fly sequence generation
    7. Train TCN with early stopping and LR scheduling
    8. Evaluate on held-out test set
    9. Save model weights and scaler to checkpoints/

Run:
    cd ai-modelling
    python -m src.training.train_classifier
"""

import os
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import geopandas as gpd
import joblib
from shapely import wkt
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score,
    f1_score, precision_score, recall_score, confusion_matrix
)

from src.models.bushfire.tcn_classifier import TCNClassifier, ClassifierConfig

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

ENV_CSV_PATHS = [
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2018_Jul_Dec_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2019_Jan_Jun_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2019_Jul_Dec_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2020_Jan_Jun_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2020_Jul_Dec_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2021_Jan_Jun_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2021_Jul_Dec_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2022_Jan_Jun_12Hourly_5kmGrid.csv',
    'src/data/bushfire/ERA5data/FireFusion_ERA5_Land_Victoria_2022_Jul_Dec_12Hourly_5kmGrid.csv',
]
FIRE_CSV_PATH = 'src/data/bushfire/satellite_detections_within_fires.csv'
CHECKPOINT_DIR = 'src/models/bushfire/checkpoints'
MODEL_PATH    = os.path.join(CHECKPOINT_DIR, 'tcn_classifier.pt')
SCALER_PATH   = os.path.join(CHECKPOINT_DIR, 'tcn_scaler.pkl')

# Fire data ends 31 Jul 2022 — trimming env data to match
ENV_CUTOFF = pd.Timestamp('2022-07-31')

# ─────────────────────────────────────────────
# FEATURES
# ─────────────────────────────────────────────

FEATURES = [
    'temperature_2m_c',
    'skin_temperature_c',
    'soil_temperature_level_1_c',
    'surface_solar_radiation_downwards',
    'surface_thermal_radiation_downwards',
    'u_component_of_wind_10m',
    'v_component_of_wind_10m',
]
N_FEATURES = len(FEATURES)

# ─────────────────────────────────────────────
# HYPERPARAMETERS
# ─────────────────────────────────────────────

LOOKBACK_STEPS          = 60     # 30 days at 12-hour intervals
BATCH_SIZE              = 64
EPOCHS                  = 1
LEARNING_RATE           = 1e-3
EARLY_STOPPING_PATIENCE = 5
LR_SCHEDULER_PATIENCE   = 3
LR_SCHEDULER_FACTOR     = 0.5
NEG_SUBSAMPLE_RATIO     = 20     # no-fire : fire sequences kept
DECISION_THRESHOLD      = 0.5

# Train/val/test split — fixed date boundaries
TRAIN_END  = pd.Timestamp('2021-06-30')
VAL_START  = pd.Timestamp('2021-01-01')
TEST_START = pd.Timestamp('2021-07-01')
# train : Jul 2018 – Dec 2020
# val   : Jan 2021 – Jun 2021
# test  : Jul 2021 – Jul 2022

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ─────────────────────────────────────────────
# 1. DATA LOADING
# ─────────────────────────────────────────────

def load_env(env_csv_paths: list) -> pd.DataFrame:
    """
    Load and concatenate multiple ERA5-Land GEE CSVs.
    Trims to ENV_CUTOFF to match fire data availability.
    """
    keep = [
        'system:index', 'datetime', 'grid_id', 'interval_start',
        'skin_temperature_c', 'soil_temperature_level_1_c',
        'surface_solar_radiation_downwards',
        'surface_thermal_radiation_downwards',
        'temperature_2m_c', 'u_component_of_wind_10m',
        'v_component_of_wind_10m', '.geo'
    ]

    dfs = []
    for path in env_csv_paths:
        df = pd.read_csv(path, usecols=keep)
        dfs.append(df)
        print(f"  Loaded {path.split('/')[-1]} — {len(df):,} rows")

    combined = pd.concat(dfs, ignore_index=True)
    combined['datetime'] = pd.to_datetime(combined['datetime'])
    combined = combined[combined['datetime'] <= ENV_CUTOFF]
    combined = combined.dropna(subset=FEATURES).reset_index(drop=True)

    # Drop any duplicate rows in case CSVs have overlapping export periods
    combined = combined.drop_duplicates(subset=['grid_id', 'datetime'])

    print(f"\n  ENV total : {combined.shape[0]:,} rows | "
          f"{combined['datetime'].min().date()} → {combined['datetime'].max().date()}")
    return combined


def load_fire(fire_csv_path: str) -> pd.DataFrame:
    """
    Load satellite fire detections.
    daynight: 0 → 00:00 interval, 1 → 12:00 interval.
    Reconstructs datetime to match ENV 12-hour intervals.
    """
    keep = ['datetime', 'daynight', 'is_burning', 'geometry']
    df = pd.read_csv(fire_csv_path, usecols=keep)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['datetime'] = df['datetime'] + pd.to_timedelta(df['daynight'] * 12, unit='h')
    print(f"  FIRE loaded : {df.shape[0]:,} rows | "
          f"{df['datetime'].min().date()} → {df['datetime'].max().date()}")
    return df[['datetime', 'is_burning', 'geometry']]


# ─────────────────────────────────────────────
# 2. SPATIAL JOIN
# ─────────────────────────────────────────────

def spatial_join_grids(env_df: pd.DataFrame, fire_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match fire detections to ERA5 grid cells via spatial join.
    env '.geo' contains GEE polygon JSON strings.
    fire 'geometry' contains WKT polygon strings.
    Returns fire_df with an added 'grid_id' column.
    """
    print("  Parsing env grid geometries...")

    def parse_geo(geo_str):
        try:
            from shapely.geometry import Polygon
            coords = json.loads(geo_str)['coordinates'][0]
            return Polygon(coords)
        except Exception:
            return None

    env_geo = env_df[['grid_id', '.geo']].drop_duplicates('grid_id').copy()
    env_geo['geometry'] = env_geo['.geo'].apply(parse_geo)
    env_geo = env_geo.dropna(subset=['geometry'])
    env_gdf = gpd.GeoDataFrame(env_geo[['grid_id', 'geometry']], crs='EPSG:4326')

    print("  Parsing fire geometries...")
    fire_df = fire_df.copy().reset_index(drop=True)
    fire_df['geometry'] = fire_df['geometry'].apply(wkt.loads)
    fire_gdf = gpd.GeoDataFrame(fire_df, crs='EPSG:4326')

    print("  Running spatial join...")
    fire_gdf['centroid'] = (
        fire_gdf.geometry.to_crs('EPSG:3857').centroid.to_crs('EPSG:4326')
    )
    fire_points = fire_gdf.set_geometry('centroid')
    joined      = gpd.sjoin(fire_points, env_gdf, how='left', predicate='within')
    fire_df['grid_id'] = joined['grid_id']

    unmatched = fire_df['grid_id'].isna().sum()
    if unmatched > 0:
        print(f"  Warning: {unmatched} fire records could not be matched to a grid cell.")

    matched = fire_df.dropna(subset=['grid_id'])
    print(f"  Matched fire records : {len(matched):,}")
    return matched


# ─────────────────────────────────────────────
# 3. LABEL TABLE
# ─────────────────────────────────────────────

def build_label_table(env_df: pd.DataFrame, fire_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create complete label table: every grid_id × datetime gets is_burning = 0 or 1.
    ERA5 env data is the spine — unmatched rows become is_burning = 0.
    """
    fire_lookup = (
        fire_df.groupby(['grid_id', 'datetime'])['is_burning']
        .max().reset_index()
    )
    merged = env_df[['grid_id', 'datetime'] + FEATURES].merge(
        fire_lookup, on=['grid_id', 'datetime'], how='left'
    )
    merged['is_burning'] = merged['is_burning'].fillna(0).astype(np.int8)
    pos   = merged['is_burning'].sum()
    total = len(merged)
    print(f"  Total rows : {total:,} | Fire : {pos:,} ({pos/total*100:.3f}%)")
    return merged


# ─────────────────────────────────────────────
# 4. TIME-BASED SPLIT
# ─────────────────────────────────────────────

def time_based_split(df: pd.DataFrame):
    """
    Split labelled dataframe into train / val / test using fixed date boundaries.
    Avoids leakage — splits are on datetime, so no grid cell's sequence spans splits.

        train : Jul 2018 – Dec 2020  (~2.5 years)
        val   : Jan 2021 – Jun 2021  (~6 months)
        test  : Jul 2021 – Jul 2022  (~1 year, held out entirely)
    """
    train_df = df[df['datetime'] < VAL_START].copy()
    val_df   = df[(df['datetime'] >= VAL_START) & (df['datetime'] <= TRAIN_END)].copy()
    test_df  = df[df['datetime'] >= TEST_START].copy()

    print(f"  Train : {train_df['datetime'].min().date()} → {train_df['datetime'].max().date()} "
          f"({len(train_df):,} rows, {train_df['is_burning'].sum():,} fires)")
    print(f"  Val   : {val_df['datetime'].min().date()} → {val_df['datetime'].max().date()} "
          f"({len(val_df):,} rows, {val_df['is_burning'].sum():,} fires)")
    print(f"  Test  : {test_df['datetime'].min().date()} → {test_df['datetime'].max().date()} "
          f"({len(test_df):,} rows, {test_df['is_burning'].sum():,} fires)")

    return train_df, val_df, test_df


# ─────────────────────────────────────────────
# 5. PYTORCH DATASET
# ─────────────────────────────────────────────

class FireDataset(Dataset):
    """
    On-the-fly sliding-window sequence generator.
    Never materialises the full (N, lookback, features) array.

    Scaler must be fitted on training data before building val/test datasets.
    Pass fit_scaler=True for training data only, then pass the fitted
    scaler object with fit_scaler=False for val and test.

    Subsamples negatives to NEG_SUBSAMPLE_RATIO : 1 to reduce class imbalance.
    """
    def __init__(self, df: pd.DataFrame, lookback: int,
                 scaler: StandardScaler = None, fit_scaler: bool = True):
        self.lookback = lookback
        self.groups   = []
        all_features  = []

        for _, group in df.groupby('grid_id'):
            group = group.sort_values('datetime')
            if len(group) <= lookback:
                continue
            feat = group[FEATURES].values.astype(np.float32)
            lbl  = group['is_burning'].values.astype(np.float32)
            self.groups.append((feat, lbl))
            all_features.append(feat)

        # Fit scaler on training data only — never on val or test
        if fit_scaler:
            combined    = np.vstack(all_features)
            self.scaler = StandardScaler()
            self.scaler.fit(combined)
        else:
            assert scaler is not None, "Must pass a fitted scaler when fit_scaler=False"
            self.scaler = scaler

        # Pre-scale all group arrays once
        self.groups = [
            (self.scaler.transform(feat), lbl)
            for feat, lbl in self.groups
        ]

        # Build flat index of (group_idx, timestep, label)
        self.index = []
        for g_idx, (feat, lbl) in enumerate(self.groups):
            for t in range(lookback, len(feat)):
                self.index.append((g_idx, t, int(lbl[t])))

        # Subsample negatives to NEG_SUBSAMPLE_RATIO : 1
        fire_idx    = [i for i, (_, _, l) in enumerate(self.index) if l == 1]
        no_fire_idx = [i for i, (_, _, l) in enumerate(self.index) if l == 0]

        max_no_fire = len(fire_idx) * NEG_SUBSAMPLE_RATIO
        if len(no_fire_idx) > max_no_fire:
            rng         = np.random.default_rng(42)
            no_fire_idx = rng.choice(no_fire_idx, max_no_fire, replace=False).tolist()

        self.index = [self.index[i] for i in sorted(fire_idx + no_fire_idx)]
        print(f"  Sequences : {len(self.index):,} "
              f"(fire: {len(fire_idx):,}, no-fire: {len(no_fire_idx):,})")

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, idx: int):
        g_idx, t, _ = self.index[idx]
        feat, lbl   = self.groups[g_idx]
        # Transpose to (features, lookback) for PyTorch Conv1d
        x = torch.from_numpy(feat[t - self.lookback : t].T.copy())
        y = torch.tensor([lbl[t]], dtype=torch.float32)
        return x, y


# ─────────────────────────────────────────────
# EVALUATION HELPER
# ─────────────────────────────────────────────

def run_evaluation(model: nn.Module, loader: DataLoader, label: str) -> dict:
    """Run inference on a loader, print and return metrics."""
    model.eval()
    all_probs, all_labels = [], []
    with torch.no_grad():
        for X_batch, y_batch in loader:
            probs = model(X_batch.to(DEVICE)).cpu().numpy().flatten()
            all_probs.extend(probs)
            all_labels.extend(y_batch.numpy().flatten())

    all_probs  = np.array(all_probs)
    all_labels = np.array(all_labels)
    preds      = (all_probs >= DECISION_THRESHOLD).astype(int)

    auc  = roc_auc_score(all_labels, all_probs)
    f1   = f1_score(all_labels, preds, zero_division=0)
    prec = precision_score(all_labels, preds, zero_division=0)
    rec  = recall_score(all_labels, preds, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(all_labels, preds, labels=[0, 1]).ravel()

    print(f"\n{'='*60}")
    print(f"  FIREFUSION — {label} RESULTS")
    print(f"{'='*60}")
    print(f"  ROC-AUC          : {auc:.4f}")
    print(f"  F1 (fire)        : {f1:.4f}")
    print(f"  Recall           : {rec:.4f}  ({rec*100:.1f}% of fires detected)")
    print(f"  Precision        : {prec:.4f}")
    print(f"  True  Positives  : {tp:,}")
    print(f"  False Positives  : {fp:,}  (false alarms)")
    print(f"  True  Negatives  : {tn:,}")
    print(f"  False Negatives  : {fn:,}  (missed fires)")
    print(f"  False Alarm Rate : {fp/(fp+tn)*100:.2f}%")
    print(f"  Threshold used   : {DECISION_THRESHOLD}")
    print(f"{'='*60}")
    print(classification_report(all_labels, preds,
                                target_names=['No Fire', 'Fire'], zero_division=0))

    return {'auc': auc, 'f1': f1, 'recall': rec, 'precision': prec,
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn}


# ─────────────────────────────────────────────
# 6-9. TRAINING PIPELINE
# ─────────────────────────────────────────────

def train():
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # 1. Load data
    print("\n[1/6] Loading data...")
    env_df  = load_env(ENV_CSV_PATHS)
    fire_df = load_fire(FIRE_CSV_PATH)

    # 2. Spatial join
    print("\n[2/6] Spatially joining fire detections to ERA5 grid...")
    fire_df = spatial_join_grids(env_df, fire_df)

    # 3. Build label table
    print("\n[3/6] Building label table...")
    labelled_df = build_label_table(env_df, fire_df)

    # 4. Time-based split — test set held out before any scaling
    print("\n[4/6] Splitting data (time-based, no leakage)...")
    train_df, val_df, test_df = time_based_split(labelled_df)

    # 5. Build datasets — scaler fitted on train only
    print("\n[5/6] Building datasets...")
    print("  Training set:")
    train_dataset = FireDataset(train_df, LOOKBACK_STEPS, fit_scaler=True)
    fitted_scaler = train_dataset.scaler
    joblib.dump(fitted_scaler, SCALER_PATH)
    print(f"  Scaler saved → {SCALER_PATH}")

    print("  Validation set:")
    val_dataset = FireDataset(val_df, LOOKBACK_STEPS,
                              scaler=fitted_scaler, fit_scaler=False)
    print("  Test set (held out — not used during training):")
    test_dataset = FireDataset(test_df, LOOKBACK_STEPS,
                               scaler=fitted_scaler, fit_scaler=False)

    # Class weight from training labels
    train_flags   = np.array([l for _, _, l in train_dataset.index], dtype=np.int8)
    fire_count    = train_flags.sum()
    no_fire_count = len(train_flags) - fire_count
    pos_weight    = torch.tensor([no_fire_count / fire_count], device=DEVICE)
    print(f"\n  Positive class weight : {pos_weight.item():.1f}x")
    print(f"  Train batches         : {len(train_dataset) // BATCH_SIZE:,}")
    print(f"  Val batches           : {len(val_dataset) // BATCH_SIZE:,}")
    print(f"  Test batches          : {len(test_dataset) // BATCH_SIZE:,}")

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE,
                              shuffle=True, num_workers=0)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_dataset,  batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=0)

    # 6. Build model
    config = ClassifierConfig(n_features=N_FEATURES, lookback_steps=LOOKBACK_STEPS)
    model  = TCNClassifier(config).to(DEVICE)
    print(f"\n  Model parameters  : {model.parameter_count():,}")
    print(f"  Receptive field   : {model.receptive_field()} steps")
    print(f"  Device            : {DEVICE}")

    criterion = nn.BCELoss(reduction='none')
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=LR_SCHEDULER_PATIENCE,
        factor=LR_SCHEDULER_FACTOR, mode='max'
    )

    # 7. Training loop
    print(f"\n[6/6] Training TCN | {EPOCHS} max epochs | patience={EARLY_STOPPING_PATIENCE}")
    best_auc   = 0.0
    no_improve = 0

    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0.0

        for batch_idx, (X_batch, y_batch) in enumerate(train_loader):
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)

            optimizer.zero_grad()
            preds   = model(X_batch)
            weights = torch.where(y_batch == 1, pos_weight, torch.ones_like(y_batch))
            loss    = (criterion(preds, y_batch) * weights).mean()
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

            if batch_idx % 100 == 0:
                print(f"    Batch {batch_idx}/{len(train_loader)}", flush=True)

        # Validation
        model.eval()
        val_probs, val_labels = [], []
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                probs = model(X_batch.to(DEVICE)).cpu().numpy().flatten()
                val_probs.extend(probs)
                val_labels.extend(y_batch.numpy().flatten())

        val_probs  = np.array(val_probs)
        val_labels = np.array(val_labels)
        val_preds  = (val_probs >= DECISION_THRESHOLD).astype(int)

        auc  = roc_auc_score(val_labels, val_probs)
        f1   = f1_score(val_labels, val_preds, zero_division=0)
        rec  = recall_score(val_labels, val_preds, zero_division=0)
        prec = precision_score(val_labels, val_preds, zero_division=0)
        scheduler.step(auc)

        print(f"  Epoch {epoch+1:02d}/{EPOCHS} | "
              f"Loss: {train_loss/len(train_loader):.4f} | "
              f"AUC: {auc:.4f} | F1: {f1:.4f} | "
              f"Recall: {rec:.4f} | Precision: {prec:.4f}")

        if auc > best_auc:
            best_auc   = auc
            no_improve = 0
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"    ✓ Best model saved (AUC: {best_auc:.4f})")
        else:
            no_improve += 1
            if no_improve >= EARLY_STOPPING_PATIENCE:
                print(f"  Early stopping at epoch {epoch+1}.")
                break

    # 8. Evaluate on val set with best model
    print("\nLoading best model for final evaluation...")
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    val_metrics  = run_evaluation(model, val_loader,  "VALIDATION SET")

    # 9. Evaluate on test set — runs once, never used for tuning
    test_metrics = run_evaluation(model, test_loader, "TEST SET (held out)")

    auc_gap = val_metrics['auc'] - test_metrics['auc']
    print(f"\n  Val AUC  : {val_metrics['auc']:.4f}")
    print(f"  Test AUC : {test_metrics['auc']:.4f}")
    print(f"  AUC gap  : {auc_gap:.4f}  "
          f"({'good generalisation' if auc_gap < 0.02 else 'possible overfitting — check test recall'})")

    print(f"\n  Model saved  → {MODEL_PATH}")
    print(f"  Scaler saved → {SCALER_PATH}")

    return model, fitted_scaler


if __name__ == '__main__':
    train()
