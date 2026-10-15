"""Thin client for the deployed Templify conversion service.

Templify itself is a separate project/deployment (see the `templify` repo).
This just drives its documented 3-step JSON contract: get a presigned S3
upload URL, PUT the source zip to it, then ask it to convert and hand back
a presigned download URL for the resulting Django-app zip.
"""
import requests

TEMPLIFY_TIMEOUT = 60


class TemplifyError(Exception):
    pass


def convert_template_zip(function_url, zip_bytes, app_name="website"):
    """Runs the full conversion flow and returns the converted zip's raw bytes."""
    upload_resp = requests.post(
        function_url, json={"action": "get-upload-url"}, timeout=TEMPLIFY_TIMEOUT
    )
    _raise_for_error(upload_resp)
    upload_data = upload_resp.json()

    put_resp = requests.put(
        upload_data["uploadUrl"],
        data=zip_bytes,
        headers={"Content-Type": "application/zip"},
        timeout=TEMPLIFY_TIMEOUT,
    )
    if put_resp.status_code >= 300:
        raise TemplifyError(f"Upload to storage failed: HTTP {put_resp.status_code}")

    convert_resp = requests.post(
        function_url,
        json={"action": "convert", "key": upload_data["key"], "app_name": app_name},
        timeout=TEMPLIFY_TIMEOUT,
    )
    _raise_for_error(convert_resp)
    convert_data = convert_resp.json()

    download_resp = requests.get(convert_data["downloadUrl"], timeout=TEMPLIFY_TIMEOUT)
    if download_resp.status_code >= 300:
        raise TemplifyError(f"Downloading converted template failed: HTTP {download_resp.status_code}")

    return download_resp.content


def _raise_for_error(resp):
    if resp.status_code >= 300:
        try:
            detail = resp.json().get("error", resp.text)
        except ValueError:
            detail = resp.text
        raise TemplifyError(f"Templify returned HTTP {resp.status_code}: {detail}")
