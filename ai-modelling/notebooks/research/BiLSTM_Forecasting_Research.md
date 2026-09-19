# Evaluation of BiLSTM as an Additional Layer for the Existing ConvLSTM Model

**Stream:** AI Modelling

**Authors:** Rishu Kumar Dube and Andres Gomez Perez

**Update Date:** 31 July 2026

---

## Purpose

This document evaluates BiLSTM as a potential additional layer for the existing ConvLSTM model used in FireFusion's bushfire forecasting component. It examines its potential functionality, strengths, weaknesses, integration requirements, and evaluation strategy.

Since the existing ConvLSTM operates with 5D spatiotemporal data, the investigation also considers the dimensional implications of integrating BiLSTM, which requires a transition from 5D to 3D. As an alternative, BiConvLSTM is evaluated as an additional layer that can preserve the 5D spatial-temporal representation. Both approaches are considered to determine which provides the most suitable extension to the current forecasting architecture.

---

## BiLSTM Overview

Bidirectional Long Short-Term Memory (BiLSTM) is an extension of the traditional Long Short-Term Memory (LSTM) network designed to improve sequence modelling by processing temporal data in both forward and backward directions. Unlike a conventional LSTM, which learns dependencies only from past observations, a BiLSTM combines information from both directions to produce a more comprehensive representation of temporal patterns. This enables the network to capture long-range dependencies and complex sequential relationships that may not be fully represented using a single-directional model. A standard BiLSTM expects 3D input data, typically structured as (batch, time steps, features).

BiLSTM has been successfully applied to a wide range of sequence modelling tasks, including natural language processing, speech recognition, environmental forecasting, and time-series prediction. More recently, it has been incorporated into hybrid deep learning architectures, where convolutional models extract spatial features while BiLSTM refines temporal representations. This combination has shown promising results in spatiotemporal forecasting applications by leveraging the strengths of both spatial and sequential feature learning.

For FireFusion, BiLSTM is considered as a potential enhancement rather than a replacement for the existing ConvLSTM model. The motivation is to investigate whether incorporating bidirectional temporal learning can complement ConvLSTM's spatial-temporal feature extraction, leading to a richer representation of environmental dynamics and potentially improving bushfire forecasting performance. The effectiveness of this approach, however, should be validated through experimental evaluation within the FireFusion framework.

---
## Strategy Approach

The original strategy proposes adding a BiLSTM layer after the existing ConvLSTM, rather than replacing the current model. FireFusion uses 5D tensors (batch, time, height, width, channels), while a standard BiLSTM operates on 3D tensors (batch, time, features).

Therefore, the ConvLSTM output must be reshaped from 5D to 3D before entering the BiLSTM and reconstructed to the required 5D output afterwards. Although reshaping preserves the values, the explicit spatial structure is no longer available to the BiLSTM and may produce large feature vectors.

As an alternative, adding a BiConvLSTM layer after the existing ConvLSTM will also be considered. This approach can maintain the 5D spatiotemporal representation, avoiding the 5D-to-3D transition while preserving explicit spatial structure.

---

## Evidence from Recent Research

Within wildfire forecasting, Marjani et al. (2024) demonstrated that combining convolutional spatial feature extraction with BiLSTM temporal modelling can effectively predict wildfire spread using spatiotemporal environmental data.

Recent studies provide evidence supporting the two architectural strategies considered for FireFusion. Li et al. (2025) developed an SSA–ConvLSTM–BiLSTM model in which ConvLSTM extracts spatiotemporal features and BiLSTM provides additional bidirectional temporal learning. Their architecture used two ConvLSTM and two BiLSTM layers and outperformed standalone ConvLSTM, supporting the potential value of adding BiLSTM after the existing model. However, the study does not explicitly describe the dimensional transformation between these layers.

For the alternative strategy, Mohammad et al. (2023) investigated ConvLSTM and BiConvLSTM encoder-decoder architectures for spatiotemporal energy-demand forecasting. BiConvLSTM extends ConvLSTM by processing temporal information bidirectionally while retaining convolutional operations for spatial feature learning. This provides relevant evidence for investigating BiConvLSTM as an additional layer after FireFusion's existing ConvLSTM, particularly because it can preserve spatial-temporal structure rather than converting the representation for a standard BiLSTM.

---

## Potential Functionality in FireFusion

Both BiLSTM and BiConvLSTM could enhance the existing FireFusion ConvLSTM model through bidirectional temporal learning, but with different roles.

Adding a BiLSTM layer would primarily provide temporal refinement. The existing ConvLSTM would continue extracting spatial-temporal features, while BiLSTM would focus on learning more complex temporal dependencies from those extracted features.

Adding a BiConvLSTM layer would instead provide additional spatial-temporal refinement. Because convolutional operations remain within the recurrent structure, the model could continue learning spatial relationships while also processing temporal information bidirectionally.

Therefore, the two approaches represent different enhancement strategies: BiLSTM focuses mainly on temporal refinement after ConvLSTM feature extraction, while BiConvLSTM continues refining spatial and temporal information together. Their effectiveness within FireFusion should be determined experimentally.

---

## Strengths

### ConvLSTM → BiLSTM

- **Enhanced temporal learning:** BiLSTM processes the extracted features in both forward and backward directions, potentially capturing more complex temporal dependencies.
- **Clear division of responsibilities:** ConvLSTM performs spatial-temporal feature extraction, while BiLSTM focuses mainly on temporal refinement.
- **Lower architectural redundancy:** BiLSTM introduces a different type of processing rather than adding another convolutional recurrent layer.
- **Lower computational complexity:** Generally requires fewer computational resources than adding a BiConvLSTM, although this depends on the size of the reshaped feature vector.
- **Research support:** Li et al. (2025) demonstrated improved forecasting performance using a ConvLSTM–BiLSTM architecture compared with standalone ConvLSTM.

### ConvLSTM → BiConvLSTM

- **Maintains 5D data format:** BiConvLSTM can process the ConvLSTM output while maintaining the 5D `(batch, time, height, width, channels)` structure.
- **Preserves spatial-temporal structure:** The additional layer can continue processing spatial grids without converting them into standard sequential feature vectors.
- **Continued spatial-temporal refinement:** Spatial and temporal representations can be further learned together.
- **Bidirectional temporal processing:** Provides forward and backward temporal learning while retaining convolutional spatial operations.



## Weaknesses

### ConvLSTM → BiLSTM

- **Requires dimensional transformation:** The 5D ConvLSTM output must be reshaped into the 3D format required by BiLSTM and later reconstructed to the required 5D output.
- **Loss of explicit spatial structure:** Although reshaping preserves the numerical values, the BiLSTM no longer directly represents spatial relationships between neighbouring locations.
- **Potentially large feature vectors:** Combining height, width, and channels into a single feature dimension can significantly increase the BiLSTM input size.
- **Risk of overfitting:** The additional recurrent layer increases model capacity and may require further regularisation.
- **Additional computational cost:** Training and inference become more expensive compared with the current ConvLSTM baseline.

### ConvLSTM → BiConvLSTM

- **Higher computational complexity:** Bidirectional convolutional recurrent operations can significantly increase training and inference costs.
- **Higher memory requirements:** Maintaining spatial feature maps throughout bidirectional recurrent processing requires additional memory.
- **Potential architectural redundancy:** Both ConvLSTM and BiConvLSTM perform spatial-temporal feature learning, so the additional layer may partially repeat features already captured by the existing model.
- **Higher risk of overfitting:** The additional convolutional recurrent capacity may be difficult to justify if the available training dataset is limited.
- **More complex implementation:** BiConvLSTM introduces additional convolutional recurrent parameters and may require more extensive integration and hyperparameter tuning.

---

## Proposed Implementation

### Current FireFusion ConvLSTM Architecture

FireFusion currently uses a ConvLSTM-based forecasting pipeline to model spatiotemporal environmental data. Sequential inputs, including weather conditions and historical fire information, are processed by the ConvLSTM model to learn both spatial and temporal relationships before generating bushfire predictions. The forecasting model is integrated with the project's API, allowing prediction results to be consumed by the Backend and Frontend components.

```text
Current FireFusion Pipeline

Environmental Data
        │
        ▼
 Data Preprocessing
        │
        ▼
     ConvLSTM
        │
        ▼
 Bushfire Prediction
        │
        ▼
     FastAPI API
        │
        ▼
 Backend / Frontend
```

**There are two models to evalute and define which model is more suitable for our project**

### Option 1: ConvLSTM → BiLSTM

The first strategy adds a **BiLSTM layer after the existing ConvLSTM** to provide additional bidirectional temporal learning. Since FireFusion operates with 5D spatiotemporal data while BiLSTM requires 3D sequential input, a dimensional transformation is required before the BiLSTM and the prediction must later be reconstructed into the required 5D output format.

```text
              Proposed ConvLSTM → BiLSTM Pipeline

                  Environmental Data
                          │
                          ▼
                   Data Preprocessing
                          │
                          ▼
                    5D Input Tensor
        (batch, time, height, width, channels)
                          │
                          ▼
                  Existing ConvLSTM
             (Spatial + Temporal Learning)
                          │
                          ▼
                   5D Feature Tensor
        (batch, time, height, width, features)
                          │
                          ▼
                        Reshape
                     5D → 3D
                          │
                          ▼
                    3D Sequence
       (batch, time, height × width × features)
                          │
                          ▼
                       BiLSTM
          (Bidirectional Temporal Refinement)
                          │
                          ▼
                  Output Projection
                          │
                          ▼
                  Reshape to 5D
                          │
                          ▼
                 Bushfire Prediction
 (batch, horizon, height, width, output_channels)
                          │
                          ▼
                     FastAPI API
                          │
                          ▼
                  Backend / Frontend
```

The reshape preserves the numerical values produced by ConvLSTM, but the explicit spatial organisation is no longer available to the BiLSTM. Combining the spatial dimensions can also produce a large feature vector, increasing computational requirements.

### Option 2: ConvLSTM → BiConvLSTM

The second strategy adds a **BiConvLSTM layer after the existing ConvLSTM**. Unlike the BiLSTM option, BiConvLSTM can continue processing the spatial-temporal representation without converting it from 5D to 3D. This allows the additional layer to perform bidirectional temporal learning while maintaining explicit spatial information.

```text
           Proposed ConvLSTM → BiConvLSTM Pipeline

                  Environmental Data
                          │
                          ▼
                   Data Preprocessing
                          │
                          ▼
                    5D Input Tensor
        (batch, time, height, width, channels)
                          │
                          ▼
                  Existing ConvLSTM
             (Spatial + Temporal Learning)
                          │
                          ▼
                   5D Feature Tensor
        (batch, time, height, width, features)
                          │
                          ▼
                     BiConvLSTM
       (Bidirectional Spatial + Temporal Refinement)
                          │
                          ▼
                  Output Projection
                          │
                          ▼
                 Bushfire Prediction
 (batch, horizon, height, width, output_channels)
                          │
                          ▼
                     FastAPI API
                          │
                          ▼
                  Backend / Frontend
```

This approach maintains the 5D representation throughout the recurrent processing, avoiding the 5D-to-3D transformation required by BiLSTM. However, it introduces additional convolutional recurrent operations, resulting in greater computational and memory requirements and potential overlap with features already learned by the existing ConvLSTM.

---
### Architectural Comparison

Both strategies extend the existing ConvLSTM but introduce different architectural implications.

| Aspect | ConvLSTM → BiLSTM | ConvLSTM → BiConvLSTM |
|---|---|---|
| **Input to additional layer** | Requires 5D → 3D transformation | Maintains 5D representation |
| **Spatial structure** | Not explicitly available within BiLSTM after reshape | Preserved throughout recurrent processing |
| **Temporal learning** | Focuses mainly on bidirectional temporal refinement | Bidirectional temporal learning with spatial context |
| **Spatial learning** | Primarily handled by the existing ConvLSTM | Continues in the additional BiConvLSTM layer |
| **Architectural redundancy** | Lower, as the layers have more distinct roles | Higher potential overlap with existing ConvLSTM |
| **Computational complexity** | Generally lower, but depends on reshaped feature size | Generally higher due to bidirectional convolutional operations |
| **Memory requirements** | Generally lower | Higher due to continued spatial processing |
| **Overfitting risk** | Increased compared with baseline | Potentially higher due to greater model capacity |
| **5D compatibility** | Requires reconstruction to 5D output | Naturally maintains the 5D spatiotemporal format |

Neither approach can be considered superior without experimental validation. Their performance should therefore be compared against the existing ConvLSTM baseline using the same FireFusion data and evaluation conditions.

---
## Model Evaluation

The two proposed architectures should be evaluated against the **existing ConvLSTM baseline** under the same experimental conditions:

1. **Current ConvLSTM**
2. **ConvLSTM → BiLSTM**
3. **ConvLSTM → BiConvLSTM**

The evaluation should consider both **forecasting performance and computational efficiency**. Prediction accuracy should be assessed using the existing regression metrics, including **Mean Squared Error (MSE), Root Mean Squared Error (RMSE), and Mean Absolute Error (MAE)**.

Computational performance should also be compared using:

- Training time
- Inference time
- Memory usage
- Number of trainable parameters
- Model complexity

In addition, the evaluation should verify that each architecture produces the required **5D FireFusion output format**.

The additional layers should only be considered beneficial if they provide a consistent improvement over the current ConvLSTM while maintaining acceptable computational cost, generalisation performance, and dimensional compatibility.

---
### Expected Benefits and Trade-offs

| Aspect | Current ConvLSTM | ConvLSTM → BiLSTM | ConvLSTM → BiConvLSTM |
|---|---|---|---|
| **Spatial feature learning** | Strong | Primarily handled by ConvLSTM | Continued spatial refinement |
| **Temporal feature learning** | Baseline | Bidirectional temporal refinement | Bidirectional temporal refinement with spatial context |
| **Data dimensionality** | Maintains 5D | Requires 5D → 3D → 5D transformation | Maintains 5D |
| **Spatial structure after additional layer** | Preserved | Not explicitly preserved within BiLSTM | Preserved |
| **Model complexity** | Lower | Higher | Highest |
| **Computational cost** | Lower | Moderate, depending on feature size | Higher |
| **Memory requirements** | Lower | Moderate | Higher |
| **Architectural redundancy** | Baseline | Lower | Potentially higher |
| **Overfitting risk** | Lower | Increased | Potentially higher |
| **Expected benefit** | Current benchmark | Stronger temporal modelling | Stronger spatial-temporal refinement |



### Controlled Evaluation Strategy

The proposed ConvLSTM–BiLSTM model should be evaluated against the current ConvLSTM baseline using the same training, validation, and testing datasets. To ensure a fair comparison, both models should follow identical data preprocessing, partitioning strategies, and evaluation procedures, with the architecture being the only variable under investigation.

**Training configuration.** The proposed model should follow the same optimisation strategy and hyperparameter configuration as the existing ConvLSTM implementation wherever possible. This ensures that any observed performance differences are attributable to the architectural modification rather than changes in the training process.

**Evaluation metrics.** Forecasting performance should be assessed using **Mean Squared Error (MSE)**, **Root Mean Squared Error (RMSE)**, and **Mean Absolute Error (MAE)**. If spatial prediction outputs are generated, additional metrics such as **Intersection over Union (IoU)** may also be considered to evaluate spatial prediction quality.

**Reproducibility.** Each architecture should be trained using multiple random seeds, with results reported as the mean and standard deviation. This reduces the influence of training variability and provides a more reliable comparison between models.

**Computational performance.** In addition to prediction accuracy, computational efficiency should be evaluated by comparing training time, inference latency, memory usage, and model complexity. These measurements help determine whether any improvement in forecasting performance justifies the additional computational cost introduced by the BiLSTM layer.

---

## Conclusion and Recommendation

## Conclusion and Recommendation

The literature reviewed in this investigation indicates that both **BiLSTM and BiConvLSTM are promising enhancements for spatiotemporal forecasting** when integrated with convolutional recurrent architectures. Recent studies have demonstrated that hybrid models can improve temporal learning and forecasting performance in wildfire and other environmental prediction tasks, supporting the investigation of similar approaches within FireFusion.

The **ConvLSTM → BiLSTM** approach provides specialised bidirectional temporal refinement but requires transforming the 5D ConvLSTM output into 3D and later reconstructing the required 5D prediction. In contrast, **ConvLSTM → BiConvLSTM** preserves the 5D spatial-temporal representation but introduces greater computational complexity and potential architectural redundancy.

Based on the current evidence, both approaches represent technically sound directions for future development. However, adoption should only be considered after experimental validation demonstrates a meaningful improvement over the existing ConvLSTM baseline using FireFusion's datasets.

If either architecture improves forecasting performance while maintaining acceptable computational efficiency, generalisation, and 5D output compatibility, it could become a valuable enhancement to FireFusion's bushfire forecasting system.

---

## References

Li W, Zhu H, Yang F, Wen C, Shi S, Zhao D, He C and Li Z (2025) ‘Storm-time ionospheric model over Yunnan-Sichuan area of China based on the SSA-ConvLSTM-BiLSTM algorithm’, *GPS Solutions*, 29(2):77, doi:10.1007/s10291-025-01836-6

Marjani M, Mahdianpari M and Mohammadimanesh F (2024) ‘CNN-BiLSTM: a novel deep learning model for near-real-time daily wildfire spread prediction’, *Remote Sensing*, 16(8):1467, doi:10.3390/rs16081467

Mohammad, F, Kang, D-K, Ahmed, MA & Kim, Y-C (2023), ‘Energy demand load forecasting for electric vehicle charging stations network based on ConvLSTM and BiConvLSTM architectures’, *IEEE*, vol. 11, pp. 67350–67369, doi:10.1109/ACCESS.2023.3274657.