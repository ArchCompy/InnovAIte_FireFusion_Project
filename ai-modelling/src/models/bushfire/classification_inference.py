"""
FireFusion — Classification Inference API
==========================================
Location : src/models/bushfire/classification_inference.py

Simple interface for making fire occurrence predictions
using a trained TCN model and saved scaler.

Designed to be called by the broader FireFusion pipeline,
taking the LSTM forecasting model's output as input.

Usage (as part of pipeline):
    from src.models.bushfire.classification_inference import ClassificationPredictor

    predictor = ClassificationPredictor(
        model_path='src/models/bushfire/checkpoints/tcn_classifier.pt',
        scaler_path='src/models/bushfire/checkpoints/tcn_scaler.pkl'
    )

    # historical_env : (n_cells, 58, 7) — last 58 observed timesteps
    # lstm_forecast  : (n_cells,  2, 7) — LSTM's 2-step prediction
    predictions, probabilities = predictor.predict(historical_env, lstm_forecast)

Run standalone (example inference):
    cd ai-modelling
    python -m src.models.bushfire.classification_inference
"""

import numpy as np
import torch
import joblib

from src.models.bushfire.tcn_classifier import TCNClassifier, ClassifierConfig

# Default checkpoint paths
DEFAULT_MODEL_PATH  = 'src/models/bushfire/checkpoints/tcn_classifier.pt'
DEFAULT_SCALER_PATH = 'src/models/bushfire/checkpoints/tcn_scaler.pkl'

# Must match LOOKBACK_STEPS used during training
LOOKBACK_STEPS     = 60
DECISION_THRESHOLD = 0.5

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class ClassificationPredictor:
    """
    Loads a trained TCNClassifier and scaler, exposes a predict() method.

    The LSTM forecasting model outputs 2 predicted future timesteps of
    environmental conditions per grid cell. ClassificationPredictor
    appends these to the most recent 58 observed timesteps to form the
    full 60-step lookback window, then classifies fire risk for each cell.

    All grid cells across Victoria are processed in a single forward pass —
    CNN parallelism means no cell-by-cell loop is needed at inference time.
    """

    def __init__(
        self,
        model_path:  str = DEFAULT_MODEL_PATH,
        scaler_path: str = DEFAULT_SCALER_PATH,
        config: ClassifierConfig = None,
    ):
        self.scaler = joblib.load(scaler_path)
        self.config = config or ClassifierConfig()

        self.model = TCNClassifier(self.config)
        self.model.load_state_dict(
            torch.load(model_path, map_location=DEVICE)
        )
        self.model.to(DEVICE)
        self.model.eval()

        print(f"✓ ClassificationPredictor loaded")
        print(f"  Model     : {model_path}")
        print(f"  Scaler    : {scaler_path}")
        print(f"  Device    : {DEVICE}")
        print(f"  Threshold : {DECISION_THRESHOLD}")

    def predict(
        self,
        historical_env: np.ndarray,
        lstm_forecast:  np.ndarray,
        threshold:      float = DECISION_THRESHOLD,
    ) -> tuple:
        """
        Generate binary fire predictions for all grid cells.

        Args:
            historical_env : np.ndarray  shape (n_cells, lookback-2, n_features)
                             Most recent observed environmental conditions.
                             Use lookback-2 = 58 timesteps (29 days).

            lstm_forecast  : np.ndarray  shape (n_cells, 2, n_features)
                             LSTM forecasting model output — predicted
                             environmental conditions for next 2 timesteps.

            threshold      : float
                             Probability cutoff for binary classification.
                             Default 0.5. Lower to catch more fires at the
                             cost of more false alarms (recommended: 0.3–0.4
                             for operational use).

        Returns:
            predictions    : np.ndarray  shape (n_cells,)  — binary 0/1
            probabilities  : np.ndarray  shape (n_cells,)  — fire probability
        """
        # Combine observed history + LSTM forecast → full lookback window
        X = np.concatenate([historical_env, lstm_forecast], axis=1)

        assert X.shape[1] == LOOKBACK_STEPS, (
            f"Expected {LOOKBACK_STEPS} timesteps after concatenation, "
            f"got {X.shape[1]}. Check historical_env has {LOOKBACK_STEPS - 2} timesteps."
        )

        n_cells, T, F = X.shape

        # Scale using training distribution — never refit at inference
        X_scaled = self.scaler.transform(
            X.reshape(-1, F)
        ).reshape(n_cells, T, F).astype(np.float32)

        # Transpose to (n_cells, features, lookback) for Conv1d
        X_tensor = torch.from_numpy(X_scaled.transpose(0, 2, 1)).to(DEVICE)

        with torch.no_grad():
            probabilities = self.model(X_tensor).cpu().numpy().flatten()

        predictions = (probabilities >= threshold).astype(int)
        return predictions, probabilities

    def predict_proba(
        self,
        historical_env: np.ndarray,
        lstm_forecast:  np.ndarray,
    ) -> np.ndarray:
        """Convenience method — returns probabilities only."""
        _, probabilities = self.predict(historical_env, lstm_forecast)
        return probabilities


# ─────────────────────────────────────────────
# STANDALONE EXAMPLE
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import os

    N_CELLS    = 10   # example: 10 grid cells
    N_FEATURES = 7    # must match training features

    model_path  = DEFAULT_MODEL_PATH
    scaler_path = DEFAULT_SCALER_PATH

    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        print(f"No trained model found at {model_path}")
        print("Run src/training/train_classifier.py first.")
    else:
        predictor = ClassificationPredictor(model_path, scaler_path)

        # Simulate LSTM output and recent history
        historical_env = np.random.randn(N_CELLS, LOOKBACK_STEPS - 2, N_FEATURES)
        lstm_forecast  = np.random.randn(N_CELLS, 2, N_FEATURES)

        predictions, probabilities = predictor.predict(historical_env, lstm_forecast)

        print(f"\nExample inference over {N_CELLS} grid cells:")
        for i in range(N_CELLS):
            status = 'FIRE' if predictions[i] == 1 else 'no fire'
            print(f"  Cell {i+1:02d} : {status}  (p={probabilities[i]:.4f})")
