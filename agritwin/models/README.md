# AgriTwin Models: Yield Forecasting & Benchmark Engine

## Overview
The `agritwin/models` module contains the machine learning and deep learning models for wheat yield prediction across the 36 districts of Punjab, Pakistan.

## Architecture

### 1. DeepAgroNet (`deepagronet.py`)
DeepAgroNet is a spatiotemporal neural network specifically designed for agricultural digital twin modeling:
- **Temporal Feature Extractor (1D-CNN)**:
  - Multi-scale 1D convolutional layers with batch normalization and ReLU activations.
  - Extracts multi-week agronomic phenological patterns (tillering, jointing, flowering, grain-filling).
- **Sequential Crop Dynamics (Bidirectional LSTM)**:
  - 2-layer Bidirectional LSTM capturing forward and backward seasonal dependencies.
  - Outputs full sequence growth representations.
- **Temporal Attention Pooling**:
  - Parametric self-attention mechanism computing importance weights $\alpha_t$ across the 27 weekly timesteps:
    $$\alpha_t = \frac{\exp(w^T \tanh(W h_t + b))}{\sum_{k=1}^{27} \exp(w^T \tanh(W h_k + b))}$$
  - Identifies critical periods (such as terminal heat stress during grain filling).
- **Static Soil & Geospatial Branch (MLP)**:
  - Dense multilayer perceptron encoding topsoil properties (clay %, sand %, silt %, SOC %, pH, bulk density, TAW) and geographic coordinates.
- **Multimodal Fusion & Uncertainty Prediction Head**:
  - Fuses temporal sequence embeddings and static soil embeddings.
  - Outputs calibrated Gaussian parameters $(\mu, \sigma)$ using Heteroscedastic Negative Log-Likelihood (NLL) Loss:
    $$\mathcal{L}_{NLL} = \frac{1}{2}\log(\sigma^2) + \frac{(y - \mu)^2}{2\sigma^2}$$
  - Generates 95% confidence intervals $[\mu - 1.96\sigma, \mu + 1.96\sigma]$ for yield forecasts.

### 2. Baseline Regressors (`baselines.py`)
- **Ridge Regression**: Regularized linear baseline with cross-validated penalty parameter $\alpha$.
- **Random Forest Regressor**: 200 estimators with depth constraint, capturing non-linear interactions between soil properties and weather aggregates.
- **XGBoost Regressor**: Gradient boosted decision trees optimized for agricultural tabular features.

### 3. Evaluation Metrics (`metrics.py`)
- **$R^2$ Score**: Coefficient of determination.
- **$RMSE$**: Root Mean Square Error in both kg/ha and maund/acre.
- **$MAE$**: Mean Absolute Error in both kg/ha and maund/acre.
- **$MBE$**: Mean Bias Error (detecting systematic over- or under-prediction).
- **Unit Conversions**:
  $$1 \text{ maund/acre} = 98.8418 \text{ kg/ha} \quad \left(\frac{40 \text{ kg}}{0.404686 \text{ ha}}\right)$$

### 4. Cross-Validation Harness (`train.py`)
- **Leave-One-Season-Out (LOSO)**: Evaluates temporal out-of-sample generalization by holding out entire seasons (2014 through 2023). Scalers are strictly fitted on training seasons to eliminate data leakage.
- **Model Registry**: Serializes production models (`deepagronet_best.pt`, `rf_best.joblib`, `xgb_best.json`) and generates `docs/MODEL_BENCHMARK.md`.
