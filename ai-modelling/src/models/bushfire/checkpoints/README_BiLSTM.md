# ConvLSTM–BiLSTM Trained Model

## Model files

- `convlstm_bilstm_forecaster.pth`: trained weights and architecture configuration.
- `convlstm_bilstm_scaler.pkl`: fitted weather scaler, input metadata and validation-selected threshold.

Use these files together. The existing ConvLSTM baseline files remain unchanged.

## Configuration

We explored different experimental configurations, first training and evaluating on 2021 data, then using 2019 for training and 2020 for validation and testing. The initial 2021 experiments showed unstable validation loss and failed to detect positive fire targets in the reported test runs, including the seed variations tested. This motivated exploring the alternative data split.

The selected model combines ConvLSTM with a per-cell BiLSTM layer, with BiLSTM hidden size 8 and 75,601 trainable parameters. Attention and BiConvLSTM are disabled.

Inputs consist of seven scaled weather features followed by historical `is_burning`, which is not scaled. Each prediction uses 30 consecutive 12-hour observations to forecast the next interval.

Training settings: seed 42, batch size 8, learning rate 0.001, maximum 50 epochs, early-stopping patience 10, and Tversky loss with α=0.3 and β=0.7.

Training stopped at epoch 27. The best validation model was selected at epoch 17.

## Data partitions

| Partition | Target dates (UTC) | Windows |
|---|---|---:|
| Training | 16 January–31 December 2019 | 700 |
| Validation | 1 January–31 March 2020 | 182 |
| Test | 1 April–31 December 2020 | 550 |

Each period starts at 00:00 and ends at 12:00 on the dates listed. The first 15 days of 2019 provide input history. Each target uses the preceding 30 observations, including history from the previous partition when needed.

The scaler was fitted on 2019 only. Model selection and threshold selection used validation only. The saved threshold is **0.8771607279777527**.

The experiment used 14,002 spatial cells with complete weather data and corrected fire-row indices.

## Evaluation results

The three columns represent evaluations of the **same trained model**, using the same saved scaler and validation-selected threshold.

- **Original test: April–December 2020.** After training on 2019 and validating on January–March 2020, the remaining months of 2020 were used for testing.
- **Additional evaluation: 2021.** The model was evaluated on another year to assess generalisation. Prediction targets cover 16 January–31 December; the first 15 days provide input history.
- **December 2021 subset.** The period **10–31 December 2021** was selected to match the published baseline’s test dates and provide a common evaluation period. These results are included in the full 2021 evaluation; they do not represent another training run.

Although the December dates match the baseline, the corrected fire labels and spatial mask differ. A controlled comparison requires both models to use the same labels and mask.

| Metric | Original test: Apr–Dec 2020 | Additional evaluation: 2021 | December 2021 subset |
|---|---:|---:|---:|
| Prediction windows | 550 | 700 | 43 |
| Positive targets | 593 | 1,107 | 60 |
| True positives | 3 | 59 | 6 |
| False positives | 41 | 249 | 0 |
| False negatives | 590 | 1,048 | 54 |
| Precision | 6.82% | 19.16% | 100.00% |
| Recall | 0.51% | 5.33% | 10.00% |
| F1 | 0.0094 | 0.0834 | 0.1818 |
| F2 | 0.0062 | 0.0623 | 0.1220 |
| PR-AUC | 0.0016 | 0.0218 | 0.1335 |

PR-AUC is calculated as average precision; values are rounded. Positive targets represent grid-cell/time observations, not distinct bushfire events.

## Loading and preprocessing

Load the model with `MultivariateTSForecaster.load(...)` and its matching scaler package with `joblib.load(...)`, using compatible project code.

Follow the saved `input_channel_order`. Apply the fitted scaler only to the seven weather features, then append historical `is_burning` without scaling it. Do not refit the scaler when evaluating new data.

Run the model in evaluation mode. Convert its output logits to probabilities with sigmoid, then apply the saved `fire_threshold`.

Preserve the experiment’s grid alignment and spatial mask. Keep excluded input cells at zero and exclude them from evaluation metrics.

## Limitations and conclusions

Across the different evaluation periods, detection remained low: the model identified only a small proportion of recorded positive targets and missed most of them. Although some evaluations showed improvements in precision and PR-AUC, these improvements did not translate into consistently high detection.

Performance varied between evaluation periods, indicating limited generalisation across years and seasonal conditions. The experiments do not establish a single cause: class imbalance, differences in the data and model limitations require further investigation.

The model provides an experimental reference for further development, but the results do not support using it as a reliable standalone bushfire detection system. Future work should prioritise improving recall while controlling false alarms, validating data preparation and evaluating consistently across multiple periods.
