import time

import requests


MAX_RETRIES = 3
PAGE_SIZE = 200


def normalize_project_id(project_id):
    """
    RFI v3 requires the project ID without the 'b.' prefix.
    """

    if not project_id:
        raise ValueError("Project ID cannot be empty.")

    project_id = str(project_id).strip()

    if project_id.startswith("b."):
        return project_id[2:]

    return project_id


def send_rfi_request(
    url,
    headers,
    payload
):
    """
    Send one RFI search request with retry handling.
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url=url,
                headers=headers,
                json=payload,
                timeout=(10, 60)
            )

        except requests.RequestException as error:
            if attempt == MAX_RETRIES:
                raise Exception(
                    f"RFI request failed after "
                    f"{MAX_RETRIES} attempts: {error}"
                ) from error

            wait_seconds = attempt * 5

            print(
                f"RFI connection error: {error}"
            )

            print(
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in [
            429,
            500,
            502,
            503,
            504
        ]:
            if attempt == MAX_RETRIES:
                raise Exception(
                    f"RFI API failed after "
                    f"{MAX_RETRIES} attempts. "
                    f"Status {response.status_code}: "
                    f"{response.text}"
                )

            retry_after = response.headers.get(
                "Retry-After"
            )

            try:
                wait_seconds = int(retry_after)
            except (TypeError, ValueError):
                wait_seconds = attempt * 5

            print(
                f"Temporary RFI API error "
                f"{response.status_code}."
            )

            print(
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        raise Exception(
            f"RFI API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    raise Exception(
        "No valid response received from RFI API."
    )


def get_all_rfis(
    project_id,
    access_token
):
    """
    Retrieve all RFIs from one ACC project.

    Pagination is controlled inside the POST JSON body:

    {
        "limit": 200,
        "offset": 0
    }
    """

    normalized_project_id = normalize_project_id(
        project_id
    )

    url = (
        "https://developer.api.autodesk.com/"
        "construction/rfis/v3/"
        f"projects/{normalized_project_id}/search:rfis"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    all_rfis = []
    seen_rfi_ids = set()

    offset = 0
    page_number = 1
    total_results = None

    while True:
        payload = {
            "limit": PAGE_SIZE,
            "offset": offset
        }

        print("=" * 70)
        print(f"Reading RFI page: {page_number}")
        print(f"Body offset: {offset}")
        print(f"Body limit: {PAGE_SIZE}")

        response = send_rfi_request(
            url=url,
            headers=headers,
            payload=payload
        )

        try:
            data = response.json()

        except ValueError as error:
            raise Exception(
                "RFI API returned invalid JSON: "
                f"{response.text}"
            ) from error

        results = data.get("results", [])

        if not isinstance(results, list):
            raise Exception(
                "Unexpected RFI API response. "
                "'results' is not a list. "
                f"Response: {data}"
            )

        pagination = data.get("pagination", {})

        if not isinstance(pagination, dict):
            pagination = {}

        response_limit = pagination.get("limit")
        response_offset = pagination.get("offset")
        response_total = pagination.get(
            "totalResults"
        )

        print(
            f"Records returned: {len(results)}"
        )

        print(
            f"Response pagination limit: "
            f"{response_limit}"
        )

        print(
            f"Response pagination offset: "
            f"{response_offset}"
        )

        print(
            f"Total RFIs reported by APS: "
            f"{response_total}"
        )

        if response_total is not None:
            try:
                total_results = int(response_total)
            except (TypeError, ValueError):
                total_results = None

        if not results:
            print(
                "No more RFI records returned."
            )
            break

        new_rfi_count = 0

        for rfi in results:
            if not isinstance(rfi, dict):
                continue

            rfi_id = rfi.get("id")

            if not rfi_id:
                continue

            rfi_id = str(rfi_id).strip()

            if rfi_id in seen_rfi_ids:
                continue

            seen_rfi_ids.add(rfi_id)
            all_rfis.append(rfi)

            new_rfi_count += 1

        print(
            f"New unique RFIs on page: "
            f"{new_rfi_count}"
        )

        print(
            f"Total unique RFIs extracted: "
            f"{len(all_rfis)}"
        )

        if new_rfi_count == 0:
            raise Exception(
                "APS returned no new RFI records. "
                f"Request body offset was {offset}."
            )

        if (
            total_results is not None
            and len(all_rfis) >= total_results
        ):
            print(
                "All RFIs reported by APS "
                "have been extracted."
            )
            break

        # Move forward by the actual number returned.
        offset += len(results)
        page_number += 1

    print("=" * 70)
    print(
        f"Final RFI count extracted: "
        f"{len(all_rfis)}"
    )
    print("=" * 70)

    return all_rfis