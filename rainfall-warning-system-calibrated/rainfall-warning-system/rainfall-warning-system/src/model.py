import json
import os
import numpy as np
import xgboost as xgb

class NowcastModel:
    def __init__(self, model_path, feature_list_path):
        self.model_path = model_path
        self.feature_list_path = feature_list_path
        self.features = json.load(open(feature_list_path, "r", encoding="utf-8"))
        self.model = None
        if os.path.exists(model_path):
            self.model = xgb.Booster()
            self.model.load_model(model_path)
            try:
                model_features = self.model.feature_names
                if model_features:
                    missing = [f for f in self.features if f not in model_features]
                    if missing:
                        raise ValueError(f"Model feature names do not match feature list. Missing: {missing[:5]}")
            except AttributeError:
                pass

    @property
    def available(self):
        return self.model is not None

    def predict(self, rows):
        if not self.available:
            raise FileNotFoundError(
                f"Model not found at {self.model_path}. Copy your trained four-hour XGBoost JSON there."
            )
        matrix = np.asarray([[float(r.get(f, 0.0) or 0.0) for f in self.features] for r in rows], dtype=np.float32)
        dm = xgb.DMatrix(matrix, feature_names=self.features)
        pred = self.model.predict(dm)
        return np.asarray(pred).reshape(-1).tolist()
