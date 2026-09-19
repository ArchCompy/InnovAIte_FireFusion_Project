# Misinformation Detection Demo

This folder contains the Streamlit interface used to demonstrate FireFusion’s misinformation-detection workflow.

The user enters a bushfire-related claim, and the interface sends it to the existing `/predict/misinformation` API. The returned result includes the predicted label, confidence, class probabilities, risk score and severity.

## Run the demo

First, start the API from the `ai-modelling` directory:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

In a second terminal, start the interface:

```bash
streamlit run demo/misinformation_app.py
```

The interface will open at:

```text
http://localhost:8501
```

The trained DeBERTa checkpoint configured in `api/config/models.yaml` must be available before starting the API.

## Run the tests

```bash
python -m pytest tests/test_misinformation_demo.py -v
```

To run the interface and existing DeBERTa tests together:

```bash
python -m pytest tests/test_deberta.py tests/test_misinformation_demo.py -v
```

## Changing the API address

The interface uses the local API on port `8080` by default. To use another address:

```bash
export FIREFUSION_MISINFORMATION_API_URL="http://host:port/predict/misinformation"
```

The classifier output is intended for demonstration and decision support. Bushfire information should still be verified through official emergency-service sources.
