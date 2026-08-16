"""Thin client for the Replicate API — the real external GPU/AI provider used
for production-grade image and video upscaling. Requires REPLICATE_API_TOKEN.
"""
import requests
from django.conf import settings

API_BASE = 'https://api.replicate.com/v1'


class ReplicateError(Exception):
    pass


def _headers():
    if not settings.REPLICATE_API_TOKEN:
        raise ReplicateError('REPLICATE_API_TOKEN is not configured.')
    return {
        'Authorization': f'Bearer {settings.REPLICATE_API_TOKEN}',
        'Content-Type': 'application/json',
    }


def create_prediction(model_version: str, input_payload: dict, webhook_url: str | None = None) -> dict:
    """Start an async prediction on Replicate. Returns the prediction resource."""
    body = {'version': model_version, 'input': input_payload}
    if webhook_url:
        body['webhook'] = webhook_url
        body['webhook_events_filter'] = ['completed']
    resp = requests.post(f'{API_BASE}/predictions', headers=_headers(), json=body, timeout=30)
    if resp.status_code >= 400:
        raise ReplicateError(f'Replicate API error {resp.status_code}: {resp.text[:300]}')
    return resp.json()


def get_prediction(prediction_id: str) -> dict:
    resp = requests.get(f'{API_BASE}/predictions/{prediction_id}', headers=_headers(), timeout=30)
    if resp.status_code >= 400:
        raise ReplicateError(f'Replicate API error {resp.status_code}: {resp.text[:300]}')
    return resp.json()


def wait_for_prediction(prediction_id: str, poll_interval: float = 2.0, timeout: float = 600.0) -> dict:
    import time
    elapsed = 0.0
    while elapsed < timeout:
        prediction = get_prediction(prediction_id)
        if prediction['status'] in ('succeeded', 'failed', 'canceled'):
            return prediction
        time.sleep(poll_interval)
        elapsed += poll_interval
    raise ReplicateError('Timed out waiting for Replicate prediction to finish.')
