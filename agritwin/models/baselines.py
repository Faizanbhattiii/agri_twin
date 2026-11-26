"""
Baseline regression models for wheat yield forecasting:
1. Ridge Regression (regularized linear baseline)
2. Random Forest Regressor (ensemble tree baseline)
3. XGBoost Regressor (gradient boosting baseline)

All baselines provide unified fit(X, y) and predict(X) methods,
feature importance extraction, and serialization.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb

from agritwin.models.metrics import calculate_metrics, to_maund_per_acre

logger = logging.getLogger(__name__)


class BaselineRidge:
    """Ridge regression with cross-validated regularizer (alpha)."""

    def __init__(self, alphas: Tuple[float, ...] = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)) -> None:
        self.model = RidgeCV(alphas=alphas)
        self.is_fitted = False
        self.best_alpha_: Optional[float] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineRidge":
        self.model.fit(X, y)
        self.is_fitted = True
        self.best_alpha_ = float(self.model.alpha_)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.predict(X).astype(np.float32)

    def save(self, filepath: Union[str, Path]) -> None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, filepath)

    def load(self, filepath: Union[str, Path]) -> "BaselineRidge":
        self.model = joblib.load(filepath)
        self.is_fitted = True
        self.best_alpha_ = float(getattr(self.model, "alpha_", 1.0))
        return self


class BaselineRandomForest:
    """Random Forest Regressor with tuned agronomic hyperparameters."""

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: Optional[int] = 12,
        min_samples_split: int = 4,
        min_samples_leaf: int = 2,
        random_state: int = 42,
    ) -> None:
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaselineRandomForest":
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.predict(X).astype(np.float32)

    @property
    def feature_importances_(self) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.feature_importances_

    def save(self, filepath: Union[str, Path]) -> None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, filepath)

    def load(self, filepath: Union[str, Path]) -> "BaselineRandomForest":
        self.model = joblib.load(filepath)
        self.is_fitted = True
        return self


class BaselineXGBoost:
    """XGBoost Regressor for tabular crop yield prediction."""

    def __init__(
        self,
        n_estimators: int = 250,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42,
    ) -> None:
        self.model = xgb.XGBRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[Tuple[np.ndarray, np.ndarray]]] = None,
        verbose: bool = False,
    ) -> "BaselineXGBoost":
        if eval_set:
            self.model.fit(X, y, eval_set=eval_set, verbose=verbose)
        else:
            self.model.fit(X, y, verbose=verbose)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.predict(X).astype(np.float32)

    @property
    def feature_importances_(self) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.feature_importances_

    def save(self, filepath: Union[str, Path]) -> None:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(filepath))

    def load(self, filepath: Union[str, Path]) -> "BaselineXGBoost":
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(filepath))
        self.is_fitted = True
        return self
