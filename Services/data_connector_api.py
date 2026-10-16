import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


BASE_URL = "https://developer.api.autodesk.com/data-connector/v1"


# =====================================================
# GENERAL HELPERS
# =====================================================

def normalize_id(value):
    """
    Removes the Autodesk Data Management 'b.' prefix
    when it is present.

    Example:
        b.123456 -> 123456
    """

    if value is None:
        return ""

    value = str(value).strip()

    if value.startswith("b."):
        return value[2:]

    return value


def get_headers(access_token, include_content_type=False):
    """
    Builds the Autodesk API request headers.
    """

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    if include_content_type:
        headers["Content-Type"] = "application/json"

    return headers


def get_response_json(response):
    """
    Safely converts an HTTP response to JSON.
    """

    try:
        return response.json()
    except ValueError:
        raise RuntimeError(
            "Autodesk returned a response that is not valid JSON.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )


# =====================================================
# CREATE DATA CONNECTOR REQUEST
# =====================================================

def create_admin_data_request(
    account_id,
    project_id,
    access_token,
    description="ACC Admin extraction",
    send_email=True
):
    """
    Creates a one-time Autodesk Data Connector request
    for the Admin service group.

    Returns:
        Dictionary containing the request details.
    """

    account_id = normalize_id(account_id)
    project_id = normalize_id(project_id)

    if not account_id:
        raise ValueError("account_id cannot be empty.")

    if not project_id:
        raise ValueError("project_id cannot be empty.")

    if not access_token:
        raise ValueError("access_token cannot be empty.")

    url = (
        f"{BASE_URL}/accounts/"
        f"{account_id}/requests"
    )

    effective_from = (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    payload = {
        "description": description,
        "isActive": True,
        "scheduleInterval": "ONE_TIME",
        "serviceGroups": ["admin"],
        "effectiveFrom": effective_from,
        "projectId": project_id,
        "sendEmail": send_email
    }

    print("\n===== REQUEST URL =====")
    print(url)

    print("\n===== REQUEST PAYLOAD =====")
    print(json.dumps(payload, indent=4))

    response = requests.post(
        url,
        headers=get_headers(
            access_token,
            include_content_type=True
        ),
        json=payload,
        timeout=60
    )

    print("\n===== RESPONSE STATUS =====")
    print(response.status_code)

    print("\n===== RESPONSE BODY =====")
    print(response.text)

    if response.status_code not in (200, 201, 202):
        raise RuntimeError(
            "Data Connector request creation failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    return get_response_json(response)


# =====================================================
# GET REQUEST JOBS
# =====================================================

def get_request_jobs(
    account_id,
    request_id,
    access_token
):
    """
    Gets the jobs created for a Data Connector request.

    Returns:
        List of job dictionaries.
    """

    account_id = normalize_id(account_id)
    request_id = str(request_id or "").strip()

    if not account_id:
        raise ValueError("account_id cannot be empty.")

    if not request_id:
        raise ValueError("request_id cannot be empty.")

    url = (
        f"{BASE_URL}/accounts/"
        f"{account_id}/requests/"
        f"{request_id}/jobs"
    )

    response = requests.get(
        url,
        headers=get_headers(access_token),
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Data Connector jobs lookup failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    data = get_response_json(response)

    if isinstance(data, list):
        return data

    return (
        data.get("results")
        or data.get("jobs")
        or data.get("data")
        or []
    )


# =====================================================
# WAIT FOR JOB
# =====================================================

def wait_for_data_connector_job(
    account_id,
    request_id,
    access_token,
    polling_interval=15,
    maximum_wait_seconds=1800
):
    """
    Waits until the Data Connector job completes.

    Returns:
        Completed job dictionary.
    """

    if polling_interval <= 0:
        raise ValueError(
            "polling_interval must be greater than zero."
        )

    if maximum_wait_seconds <= 0:
        raise ValueError(
            "maximum_wait_seconds must be greater than zero."
        )

    started_at = time.monotonic()

    while True:
        elapsed = time.monotonic() - started_at

        if elapsed >= maximum_wait_seconds:
            raise TimeoutError(
                "Data Connector job did not complete within "
                f"{maximum_wait_seconds} seconds."
            )

        jobs = get_request_jobs(
            account_id=account_id,
            request_id=request_id,
            access_token=access_token
        )

        if not jobs:
            print(
                "No job has appeared yet. "
                f"Checking again in {polling_interval} seconds..."
            )

            time.sleep(polling_interval)
            continue

        job = jobs[0]

        status = str(
            job.get("status") or ""
        ).strip().lower()

        completion_status = str(
            job.get("completionStatus") or ""
        ).strip().lower()

        print(
            "Job status: "
            f"{status or 'unknown'} | "
            "Completion status: "
            f"{completion_status or 'not available'}"
        )

        if (
            status == "complete"
            and completion_status == "success"
        ):
            return job

        if status in {
            "failed",
            "error",
            "cancelled",
            "canceled"
        }:
            raise RuntimeError(
                "Data Connector job failed.\n"
                f"Job details: {json.dumps(job, indent=4)}"
            )

        if (
            status == "complete"
            and completion_status
            and completion_status != "success"
        ):
            raise RuntimeError(
                "Data Connector job completed unsuccessfully.\n"
                f"Job details: {json.dumps(job, indent=4)}"
            )

        time.sleep(polling_interval)


# =====================================================
# GET GENERATED FILE LISTING
# =====================================================

def get_job_data_listing(
    account_id,
    job_id,
    access_token
):
    """
    Gets the generated files for a completed
    Data Connector job.

    Returns:
        List of generated file dictionaries.
    """

    account_id = normalize_id(account_id)
    job_id = str(job_id or "").strip()

    if not account_id:
        raise ValueError("account_id cannot be empty.")

    if not job_id:
        raise ValueError("job_id cannot be empty.")

    url = (
        f"{BASE_URL}/accounts/"
        f"{account_id}/jobs/"
        f"{job_id}/data-listing"
    )

    print("\n===== DATA LISTING URL =====")
    print(url)

    response = requests.get(
        url,
        headers=get_headers(access_token),
        timeout=60
    )

    print("\n===== DATA LISTING STATUS =====")
    print(response.status_code)

    print("\n===== DATA LISTING RESPONSE =====")
    print(response.text)

    if response.status_code != 200:
        raise RuntimeError(
            "Data listing request failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    data = get_response_json(response)

    if isinstance(data, list):
        return data

    return (
        data.get("results")
        or data.get("data")
        or data.get("files")
        or []
    )


# =====================================================
# FIND ZIP FILE
# =====================================================

def find_zip_file(data_listing):
    """
    Finds the main ZIP file in the Data Connector
    file listing.

    Returns:
        {
            "name": "...zip",
            "key": "..."
        }

        Returns None when no ZIP is found.
    """

    if not isinstance(data_listing, list):
        raise TypeError(
            "data_listing must be a list."
        )

    preferred_zip = None
    fallback_zip = None

    for item in data_listing:
        if not isinstance(item, dict):
            continue

        file_name = str(
            item.get("name")
            or item.get("fileName")
            or item.get("filename")
            or item.get("key")
            or ""
        ).strip()

        file_key = (
            item.get("key")
            or item.get("id")
            or item.get("fileKey")
            or file_name
        )

        if not file_name:
            continue

        if not file_name.lower().endswith(".zip"):
            continue

        zip_info = {
            "name": file_name,
            "key": file_key
        }

        if (
            file_name.lower()
            == "autodesk_data_extract.zip"
        ):
            preferred_zip = zip_info
            break

        if fallback_zip is None:
            fallback_zip = zip_info

    return preferred_zip or fallback_zip


# =====================================================
# GET SIGNED DOWNLOAD URL
# =====================================================

def get_signed_download_details(
    account_id,
    job_id,
    file_key,
    access_token
):
    """
    Requests a temporary signed download URL
    for one generated Data Connector file.

    Returns:
        signed_url, download_headers
    """

    account_id = normalize_id(account_id)
    job_id = str(job_id or "").strip()
    file_key = str(file_key or "").strip()

    if not account_id:
        raise ValueError("account_id cannot be empty.")

    if not job_id:
        raise ValueError("job_id cannot be empty.")

    if not file_key:
        raise ValueError("file_key cannot be empty.")

    encoded_key = quote(
        file_key,
        safe=""
    )

    url = (
        f"{BASE_URL}/accounts/"
        f"{account_id}/jobs/"
        f"{job_id}/data/"
        f"{encoded_key}"
    )

    print("\n===== SIGNED URL REQUEST =====")
    print(url)

    response = requests.get(
        url,
        headers=get_headers(access_token),
        timeout=60
    )

    print("\n===== SIGNED URL STATUS =====")
    print(response.status_code)

    print("\n===== SIGNED URL RESPONSE =====")
    print(response.text)

    if response.status_code != 200:
        raise RuntimeError(
            "Signed URL request failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    data = get_response_json(response)

    signed_url = (
        data.get("signedUrl")
        or data.get("signedURL")
        or data.get("downloadUrl")
        or data.get("url")
    )

    if not signed_url:
        raise RuntimeError(
            "No signed download URL was returned.\n"
            f"Response: {json.dumps(data, indent=4)}"
        )

    download_headers = (
        data.get("headers")
        or data.get("downloadHeaders")
        or {}
    )

    if not isinstance(download_headers, dict):
        download_headers = {}

    return signed_url, download_headers


# =====================================================
# BACKWARD-COMPATIBLE SIGNED URL FUNCTION
# =====================================================

def get_signed_download_url(
    account_id,
    job_id,
    file_key,
    access_token
):
    """
    Backward-compatible function.

    Returns only the signed URL.
    """

    signed_url, _ = get_signed_download_details(
        account_id=account_id,
        job_id=job_id,
        file_key=file_key,
        access_token=access_token
    )

    return signed_url


# =====================================================
# DOWNLOAD SIGNED FILE
# =====================================================

def download_signed_file(
    signed_url,
    output_file,
    download_headers=None
):
    """
    Downloads a file from Autodesk's temporary
    signed URL.

    Returns:
        Full downloaded file path as a string.
    """

    if not signed_url:
        raise ValueError("signed_url cannot be empty.")

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nDownloading file...")
    print(f"Output: {output_path}")

    response = requests.get(
        signed_url,
        headers=download_headers or {},
        stream=True,
        timeout=300
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Data Connector download failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text[:500]}"
        )

    total_bytes = 0

    with output_path.open("wb") as file:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if not chunk:
                continue

            file.write(chunk)
            total_bytes += len(chunk)

    if total_bytes == 0:
        raise RuntimeError(
            "The downloaded file is empty."
        )

    print(
        f"Download completed: {total_bytes:,} bytes"
    )

    return str(output_path)


# =====================================================
# EXTRACT ZIP
# =====================================================

def extract_zip_file(
    zip_file,
    output_folder
):
    """
    Extracts a downloaded ZIP file.

    Returns:
        Extracted folder path as a string.
    """

    zip_path = Path(zip_file)
    output_path = Path(output_folder)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"ZIP file does not exist: {zip_path}"
        )

    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(
            f"The downloaded file is not a valid ZIP: "
            f"{zip_path}"
        )

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nExtracting ZIP...")
    print(f"ZIP: {zip_path}")
    print(f"Destination: {output_path}")

    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as archive:
        archive.extractall(output_path)

    return str(output_path)