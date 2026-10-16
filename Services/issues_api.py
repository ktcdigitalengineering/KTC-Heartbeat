import time

import requests


MAX_RETRIES = 3
PAGE_LIMIT = 100


def normalize_project_id(project_id):
    """
    ACC Issues API requires the project UUID without the 'b.' prefix.
    """

    if not project_id:
        raise ValueError("Project ID cannot be empty.")

    project_id = str(project_id).strip()

    if project_id.startswith("b."):
        return project_id[2:]

    return project_id


def send_get_request(
    url,
    headers,
    params=None
):
    """
    Send one GET request with retry handling.
    """

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url=url,
                headers=headers,
                params=params,
                timeout=(10, 60)
            )

        except requests.RequestException as error:
            if attempt == MAX_RETRIES:
                raise Exception(
                    f"Issues request failed after "
                    f"{MAX_RETRIES} attempts: {error}"
                ) from error

            wait_seconds = attempt * 5

            print(
                f"Issues connection error: {error}"
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
                    f"Issues API failed after "
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
                f"Temporary Issues API error "
                f"{response.status_code}."
            )

            print(
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        raise Exception(
            f"Issues API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    raise Exception(
        "No valid response received from Issues API."
    )


def get_all_issues(
    project_id,
    access_token
):
    """
    Retrieve all issues from one ACC project.

    Pagination is based on:
        pagination.limit
        pagination.offset
        pagination.totalResults
    """

    project_id = normalize_project_id(
        project_id
    )

    url = (
        "https://developer.api.autodesk.com/"
        "construction/issues/v1/"
        f"projects/{project_id}/issues"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    all_issues = []
    seen_issue_ids = set()

    offset = 0
    page_number = 1

    while True:
        params = {
            "limit": PAGE_LIMIT,
            "offset": offset
        }

        print("=" * 70)
        print(f"Reading Issues page: {page_number}")
        print(f"Offset: {offset}")
        print(f"Requested limit: {PAGE_LIMIT}")

        response = send_get_request(
            url=url,
            headers=headers,
            params=params
        )

        try:
            data = response.json()

        except ValueError as error:
            raise Exception(
                "Issues API returned invalid JSON: "
                f"{response.text}"
            ) from error

        results = data.get("results", [])

        if not isinstance(results, list):
            raise Exception(
                "Unexpected Issues API response. "
                "'results' is not a list. "
                f"Response keys: {list(data.keys())}"
            )

        pagination = data.get("pagination", {})

        if not isinstance(pagination, dict):
            pagination = {}

        response_limit = pagination.get(
            "limit",
            len(results)
        )

        total_results = pagination.get(
            "totalResults"
        )

        print(
            f"Issues returned: {len(results)}"
        )

        print(
            f"Total reported by APS: "
            f"{total_results}"
        )

        if not results:
            break

        new_issue_count = 0

        for issue in results:
            if not isinstance(issue, dict):
                continue

            issue_id = issue.get("id")

            if not issue_id:
                continue

            issue_id = str(issue_id).strip()

            if issue_id in seen_issue_ids:
                continue

            seen_issue_ids.add(issue_id)
            all_issues.append(issue)

            new_issue_count += 1

        print(
            f"New unique issues: "
            f"{new_issue_count}"
        )

        print(
            f"Total issues extracted: "
            f"{len(all_issues)}"
        )

        if new_issue_count == 0:
            raise Exception(
                "APS returned no new Issues records. "
                f"Current offset: {offset}"
            )

        if total_results is not None:
            try:
                total_results = int(total_results)
            except (TypeError, ValueError):
                total_results = None

        if (
            total_results is not None
            and len(all_issues) >= total_results
        ):
            break

        try:
            response_limit = int(response_limit)
        except (TypeError, ValueError):
            response_limit = len(results)

        if response_limit <= 0:
            response_limit = len(results)

        offset += response_limit
        page_number += 1

    print("=" * 70)
    print(
        f"Final Issues count extracted: "
        f"{len(all_issues)}"
    )
    print("=" * 70)

    return all_issues