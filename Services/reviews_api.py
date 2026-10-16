import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

import requests
import time
import random


BASE_URL = (
    "https://developer.api.autodesk.com"
    "/construction/reviews/v1/projects"
)

DEFAULT_PAGE_LIMIT = 50
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_WORKERS = 1


def normalize_project_id(project_id: str) -> str:
    """
    Reviews API expects the project UUID without the 'b.' prefix.
    """
    if not project_id:
        raise ValueError("Project ID is empty.")

    return project_id[2:] if project_id.startswith("b.") else project_id


def get_headers(access_token: str) -> dict[str, str]:
    """
    Returns standard headers for Autodesk Reviews API calls.
    """
    if not access_token:
        raise ValueError("Access token is empty.")

    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def _extract_items(payload: Any) -> list[dict]:
    """
    Supports common Autodesk list-response structures.
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("results", "data", "reviews", "items"):
        value = payload.get(key)

        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []


def _unwrap_dict(payload: Any) -> dict:
    """
    Returns the nested 'data' object when present; otherwise returns
    the payload itself if it is a dictionary.
    """
    if not isinstance(payload, dict):
        return {}

    data = payload.get("data")

    if isinstance(data, dict):
        return data

    return payload


def serialize_value(
    value: Any,
) -> str | int | float | bool | None:
    """
    Converts nested values to JSON text for CSV output.
    """
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def _safe_lookup_user_name(
    user_id: str | None,
    admin_lookup=None,
) -> str | None:
    """
    Resolves a user name through AdminLookup without allowing
    a lookup failure to stop the Reviews export.
    """
    if not user_id or admin_lookup is None:
        return None

    try:
        return admin_lookup.get_user_name(user_id)
    except Exception:
        return None


def extract_user(
    value: Any,
    admin_lookup=None,
) -> tuple[str | None, str | None]:
    """
    Extracts a user ID and display name from either:
    - an embedded Reviews API user object
    - a plain user ID
    """

    if value is None:
        return None, None

    if isinstance(value, dict):
        user_id = (
            value.get("autodeskId")
            or value.get("id")
            or value.get("userId")
            or value.get("uid")
        )

        user_name = (
            value.get("name")
            or value.get("displayName")
            or value.get("fullName")
            or value.get("email")
        )

        if not user_name and user_id:
            user_name = _safe_lookup_user_name(
                str(user_id),
                admin_lookup,
            )

        return (
            str(user_id) if user_id is not None else None,
            str(user_name) if user_name is not None else None,
        )

    if isinstance(value, str):
        user_name = _safe_lookup_user_name(
            value,
            admin_lookup,
        )

        return value, user_name or value

    return str(value), str(value)


def extract_user_list(
    value: Any,
    admin_lookup=None,
) -> tuple[str | None, str | None]:
    """
    Converts one or more users into semicolon-separated IDs and names.
    """

    if value is None:
        return None, None

    values = value if isinstance(value, list) else [value]

    user_ids: list[str] = []
    user_names: list[str] = []

    for item in values:
        user_id, user_name = extract_user(
            item,
            admin_lookup,
        )

        if user_id and user_id not in user_ids:
            user_ids.append(user_id)

        if user_name and user_name not in user_names:
            user_names.append(user_name)

    return (
        "; ".join(user_ids) if user_ids else None,
        "; ".join(user_names) if user_names else None,
    )


def extract_named_objects(
    value: Any,
) -> tuple[str | None, str | None]:
    """
    Converts embedded Autodesk objects such as users, roles and companies
    into semicolon-separated ID and name columns.
    """

    if value is None:
        return None, None

    values = value if isinstance(value, list) else [value]

    object_ids: list[str] = []
    object_names: list[str] = []

    for item in values:
        if isinstance(item, dict):
            object_id = (
                item.get("autodeskId")
                or item.get("id")
                or item.get("userId")
                or item.get("roleId")
                or item.get("companyId")
                or item.get("oxygenId")
            )

            object_name = (
                item.get("name")
                or item.get("displayName")
                or item.get("fullName")
                or item.get("email")
            )

            if object_id is not None:
                object_id_text = str(object_id)

                if object_id_text not in object_ids:
                    object_ids.append(object_id_text)

            if object_name is not None:
                object_name_text = str(object_name)

                if object_name_text not in object_names:
                    object_names.append(object_name_text)

        elif item is not None:
            item_text = str(item)

            if item_text not in object_ids:
                object_ids.append(item_text)

    return (
        "; ".join(object_ids) if object_ids else None,
        "; ".join(object_names) if object_names else None,
    )


def _normalise_candidates(
    candidates: Any,
) -> list[dict]:
    """
    Converts candidate structures into a flat list of dictionaries.
    """

    if isinstance(candidates, list):
        return [
            candidate
            for candidate in candidates
            if isinstance(candidate, dict)
        ]

    if not isinstance(candidates, dict):
        return []

    flattened: list[dict] = []

    for key in ("users", "roles", "companies", "groups"):
        values = candidates.get(key) or []

        if isinstance(values, list):
            flattened.extend(
                value
                for value in values
                if isinstance(value, dict)
            )

    return flattened


def extract_workflow_steps(
    workflow_snapshot: dict,
) -> dict[str, str | None]:
    """
    Extracts workflow steps and workflow candidates into CSV-friendly
    semicolon-separated columns.
    """

    steps = workflow_snapshot.get("steps") or []

    if not isinstance(steps, list):
        steps = []

    step_ids: list[str] = []
    step_names: list[str] = []
    step_types: list[str] = []
    candidate_ids: list[str] = []
    candidate_names: list[str] = []

    for step in steps:
        if not isinstance(step, dict):
            continue

        step_id = (
            step.get("id")
            or step.get("stepId")
        )

        step_name = (
            step.get("name")
            or step.get("stepName")
            or step.get("title")
            or step_id
        )

        step_type = (
            step.get("type")
            or step.get("stepType")
        )

        if step_id is not None:
            step_id_text = str(step_id)

            if step_id_text not in step_ids:
                step_ids.append(step_id_text)

        if step_name is not None:
            step_name_text = str(step_name)

            if step_name_text not in step_names:
                step_names.append(step_name_text)

        if step_type is not None:
            step_type_text = str(step_type)

            if step_type_text not in step_types:
                step_types.append(step_type_text)

        candidates = _normalise_candidates(
            step.get("candidates") or []
        )

        for candidate in candidates:
            candidate_id = (
                candidate.get("autodeskId")
                or candidate.get("id")
                or candidate.get("userId")
                or candidate.get("roleId")
                or candidate.get("companyId")
            )

            candidate_name = (
                candidate.get("name")
                or candidate.get("displayName")
                or candidate.get("email")
            )

            if candidate_id is not None:
                candidate_id_text = str(candidate_id)

                if candidate_id_text not in candidate_ids:
                    candidate_ids.append(candidate_id_text)

            if candidate_name is not None:
                candidate_name_text = str(candidate_name)

                if candidate_name_text not in candidate_names:
                    candidate_names.append(candidate_name_text)

    return {
        "workflowStepIds": (
            "; ".join(step_ids)
            if step_ids
            else None
        ),
        "workflowStepNames": (
            "; ".join(step_names)
            if step_names
            else None
        ),
        "workflowStepTypes": (
            "; ".join(step_types)
            if step_types
            else None
        ),
        "workflowCandidateIds": (
            "; ".join(candidate_ids)
            if candidate_ids
            else None
        ),
        "workflowCandidateNames": (
            "; ".join(candidate_names)
            if candidate_names
            else None
        ),
    }


def get_all_reviews(
    project_id: str,
    access_token: str,
    page_limit: int = DEFAULT_PAGE_LIMIT,
) -> list[dict]:
    """
    Retrieves all reviews using offset pagination.

    Autodesk Reviews API permits a maximum page limit of 50.
    """

    normalized_project_id = normalize_project_id(project_id)
    page_limit = max(1, min(page_limit, 50))

    url = (
        f"{BASE_URL}/"
        f"{normalized_project_id}/reviews"
    )

    headers = get_headers(access_token)

    all_reviews: list[dict] = []
    offset = 0
    page_number = 1
    total_results: Optional[int] = None

    while True:
        params = {
            "limit": page_limit,
            "offset": offset,
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Reviews API error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        payload = response.json()
        reviews = _extract_items(payload)

        all_reviews.extend(reviews)

        pagination = (
            payload.get("pagination", {})
            if isinstance(payload, dict)
            else {}
        )

        if total_results is None:
            raw_total = (
                pagination.get("totalResults")
                or pagination.get("total")
            )

            if isinstance(raw_total, int):
                total_results = raw_total

        total_suffix = (
            f"/{total_results}"
            if total_results is not None
            else ""
        )

        #Printing of every single Workflow
        """print(
            f"Reviews page {page_number}: "
            f"{len(reviews)} record(s), "
            f"offset {offset}, "
            f"total retrieved "
            f"{len(all_reviews)}{total_suffix}"
        )"""

        if not reviews:
            break

        if (
            total_results is not None
            and len(all_reviews) >= total_results
        ):
            break

        if len(reviews) < page_limit:
            break

        offset += page_limit
        page_number += 1

    print(
        f"Total reviews retrieved: "
        f"{len(all_reviews)}"
    )

    return all_reviews


def get_review(
    project_id: str,
    review_id: str,
    access_token: str,
) -> dict:
    """
    Retrieves the detail record for one review.
    """

    normalized_project_id = normalize_project_id(project_id)

    url = (
        f"{BASE_URL}/"
        f"{normalized_project_id}/reviews/"
        f"{review_id}"
    )

    response = requests.get(
        url,
        headers=get_headers(access_token),
        timeout=DEFAULT_TIMEOUT,
    )

    if response.status_code == 404:
        return {}

    if response.status_code != 200:
        raise RuntimeError(
            "Review detail API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return _unwrap_dict(response.json())


def get_review_workflow(
    project_id: str,
    review_id: str,
    access_token: str,
    max_retries: int = 5,
) -> dict:
    """
    Retrieves the workflow snapshot attached to one review.

    Retries temporary Autodesk API failures using exponential backoff.
    """

    normalized_project_id = normalize_project_id(
        project_id
    )

    url = (
        f"{BASE_URL}/"
        f"{normalized_project_id}/reviews/"
        f"{review_id}/workflow"
    )

    headers = get_headers(access_token)

    retryable_status_codes = {
        429,
        500,
        502,
        503,
        504,
    }

    for attempt in range(
        1,
        max_retries + 1,
    ):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )

        except requests.RequestException as error:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Review {review_id} workflow "
                    f"request failed after "
                    f"{max_retries} attempts: {error}"
                ) from error

            wait_seconds = (
                2 ** (attempt - 1)
                + random.uniform(0, 1)
            )

            print(
                f"Review {review_id}: network error. "
                f"Retry {attempt}/{max_retries} "
                f"in {wait_seconds:.1f} seconds."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            result = _unwrap_dict(
                response.json()
            )

            time.sleep(0.5)

            return result

        if response.status_code == 404:
            return {}

        if (
            response.status_code
            not in retryable_status_codes
        ):
            raise RuntimeError(
                f"Review {review_id} workflow API "
                f"error HTTP {response.status_code}: "
                f"{response.text}"
            )

        if attempt == max_retries:
            raise RuntimeError(
                f"Review {review_id} workflow API "
                f"failed after {max_retries} attempts. "
                f"Last response was "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        retry_after = response.headers.get(
            "Retry-After"
        )

        if retry_after:
            try:
                wait_seconds = float(
                    retry_after
                )
            except ValueError:
                wait_seconds = (
                    2 ** (attempt - 1)
                )
        else:
            wait_seconds = (
                2 ** (attempt - 1)
                + random.uniform(0, 1)
            )

        print(
            f"Review {review_id}: "
            f"HTTP {response.status_code}. "
            f"Retry {attempt}/{max_retries} "
            f"in {wait_seconds:.1f} seconds."
        )

        time.sleep(wait_seconds)

    return {}

def _enrich_single_review_with_workflow(
    review: dict,
    project_id: str,
    access_token: str,
) -> dict:
    """
    Retrieves one workflow snapshot and stores it under an internal key.
    """

    enriched_review = review.copy()

    review_id = (
        review.get("id")
        or review.get("reviewId")
    )

    if not review_id:
        enriched_review["_workflowSnapshot"] = {}
        enriched_review["_workflowError"] = (
            "Review ID missing"
        )
        return enriched_review

    try:
        workflow_snapshot = get_review_workflow(
            project_id=project_id,
            review_id=str(review_id),
            access_token=access_token,
        )

        enriched_review["_workflowSnapshot"] = (
            workflow_snapshot
        )
        enriched_review["_workflowError"] = None

    except Exception as error:
        enriched_review["_workflowSnapshot"] = {}
        enriched_review["_workflowError"] = str(error)

    return enriched_review


def enrich_reviews_with_workflows(
    reviews: list[dict],
    project_id: str,
    access_token: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict]:
    """
    Retrieves workflow snapshots for all reviews in parallel while
    preserving the original review order.
    """

    if not reviews:
        return []

    max_workers = max(1, min(max_workers, 16))
    indexed_results: dict[int, dict] = {}
    total_reviews = len(reviews)

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        future_map = {
            executor.submit(
                _enrich_single_review_with_workflow,
                review,
                project_id,
                access_token,
            ): index
            for index, review in enumerate(reviews)
        }

        completed = 0

        for future in as_completed(future_map):
            index = future_map[future]
            completed += 1

            try:
                enriched_review = future.result()
            except Exception as error:
                enriched_review = reviews[index].copy()
                enriched_review["_workflowSnapshot"] = {}
                enriched_review["_workflowError"] = str(error)

            indexed_results[index] = enriched_review

            review_id = (
                enriched_review.get("id")
                or enriched_review.get("reviewId")
                or "Unknown"
            )

            workflow_snapshot = (
                enriched_review.get("_workflowSnapshot")
                or {}
            )

            workflow_name = (
                workflow_snapshot.get("name")
                if isinstance(
                    workflow_snapshot,
                    dict,
                )
                else None
            )

            workflow_error = enriched_review.get(
                "_workflowError"
            )

            if workflow_error:
                status_text = (
                    f"failed: {workflow_error}"
                )
            elif workflow_name:
                status_text = workflow_name
            else:
                status_text = "No workflow data"
            # Printing of Review Workflow of each single submission
            """print(
                f"Workflow [{completed}/{total_reviews}] "
                f"{review_id}: {status_text}"
            )"""

    enriched_reviews = [
        indexed_results[index]
        for index in range(total_reviews)
    ]


    print(
        "Workflow enrichment completed: "
        f"{len(enriched_reviews)} review(s)"
    )

    return enriched_reviews


def flatten_review(
    review: dict,
    admin_lookup=None,
) -> dict:
    """
    Flattens one Autodesk Reviews API record for CSV export.

    Handles:
    - embedded users
    - plain user IDs
    - multiple reviewers and approvers
    - workflow snapshots and steps
    - nextActionBy users, roles, companies and claimedBy
    - retention of unmapped top-level fields
    """

    review_id = (
        review.get("id")
        or review.get("reviewId")
    )

    created_by_id, created_by_name = extract_user(
        review.get("createdBy"),
        admin_lookup,
    )

    updated_by_id, updated_by_name = extract_user(
        review.get("updatedBy"),
        admin_lookup,
    )

    initiated_by_value = (
        review.get("initiatedBy")
        or review.get("initiator")
        or review.get("initiatorId")
    )

    initiated_by_id, initiated_by_name = extract_user(
        initiated_by_value,
        admin_lookup,
    )

    owner_value = (
        review.get("owner")
        or review.get("reviewOwner")
        or review.get("ownerId")
    )

    owner_id, owner_name = extract_user(
        owner_value,
        admin_lookup,
    )

    reviewers_value = (
        review.get("reviewers")
        or review.get("participants")
        or review.get("assignedReviewers")
    )

    reviewer_ids, reviewer_names = extract_user_list(
        reviewers_value,
        admin_lookup,
    )

    approvers_value = (
        review.get("approvers")
        or review.get("assignedApprovers")
    )

    approver_ids, approver_names = extract_user_list(
        approvers_value,
        admin_lookup,
    )

    workflow = review.get("workflow") or {}

    if not isinstance(workflow, dict):
        workflow = {}

    workflow_snapshot = (
        review.get("_workflowSnapshot")
        or {}
    )

    if not isinstance(workflow_snapshot, dict):
        workflow_snapshot = {}

    workflow_step_data = extract_workflow_steps(
        workflow_snapshot
    )

    current_step = review.get("currentStep") or {}

    if not isinstance(current_step, dict):
        current_step = {}

    next_action_by = review.get("nextActionBy") or {}

    if not isinstance(next_action_by, dict):
        next_action_by = {}

    claimed_by = next_action_by.get("claimedBy") or []

    candidates = next_action_by.get("candidates") or {}

    if not isinstance(candidates, dict):
        candidates = {}

    candidate_users = candidates.get("users") or []
    candidate_roles = candidates.get("roles") or []
    candidate_companies = candidates.get("companies") or []

    claimed_by_ids, claimed_by_names = extract_named_objects(
        claimed_by
    )

    candidate_user_ids, candidate_user_names = (
        extract_named_objects(candidate_users)
    )

    candidate_role_ids, candidate_role_names = (
        extract_named_objects(candidate_roles)
    )

    candidate_company_ids, candidate_company_names = (
        extract_named_objects(candidate_companies)
    )

    workflow_id = (
        review.get("workflowId")
        or workflow_snapshot.get("id")
        or workflow.get("id")
    )

    workflow_name = (
        review.get("workflowName")
        or workflow_snapshot.get("name")
        or workflow.get("name")
    )

    flattened = {
        "reviewId": review_id,
        "name": (
            review.get("name")
            or review.get("title")
        ),
        "description": review.get("description"),
        "status": review.get("status"),
        "result": (
            review.get("result")
            or review.get("approvalStatus")
            or review.get("outcome")
        ),
        "createdAt": review.get("createdAt"),
        "updatedAt": review.get("updatedAt"),
        "dueDate": (
            review.get("dueDate")
            or review.get("dueAt")
        ),
        "completedAt": (
            review.get("completedAt")
            or review.get("closedAt")
            or review.get("finishedAt")
        ),

        "createdBy": created_by_id,
        "createdByName": created_by_name,
        "updatedBy": updated_by_id,
        "updatedByName": updated_by_name,
        "initiatedBy": initiated_by_id,
        "initiatedByName": initiated_by_name,
        "ownerId": owner_id,
        "ownerName": owner_name,
        "reviewerIds": reviewer_ids,
        "reviewerNames": reviewer_names,
        "approverIds": approver_ids,
        "approverNames": approver_names,

        "workflowId": workflow_id,
        "workflowName": workflow_name,
        "workflowStepIds": (
            workflow_step_data["workflowStepIds"]
        ),
        "workflowStepNames": (
            workflow_step_data["workflowStepNames"]
        ),
        "workflowStepTypes": (
            workflow_step_data["workflowStepTypes"]
        ),
        "workflowCandidateIds": (
            workflow_step_data[
                "workflowCandidateIds"
            ]
        ),
        "workflowCandidateNames": (
            workflow_step_data[
                "workflowCandidateNames"
            ]
        ),
        "workflowError": review.get(
            "_workflowError"
        ),

        "currentStepId": (
            review.get("currentStepId")
            or current_step.get("id")
        ),
        "currentStepName": (
            review.get("currentStepName")
            or current_step.get("name")
            or current_step.get("title")
        ),

        "nextActionClaimedByIds": claimed_by_ids,
        "nextActionClaimedByNames": claimed_by_names,
        "nextActionUserIds": candidate_user_ids,
        "nextActionUserNames": candidate_user_names,
        "nextActionRoleIds": candidate_role_ids,
        "nextActionRoleNames": candidate_role_names,
        "nextActionCompanyIds": candidate_company_ids,
        "nextActionCompanyNames": candidate_company_names,

        "fileCount": (
            review.get("fileCount")
            or review.get("versionCount")
        ),

        "rawReviewJson": json.dumps(
            {
                key: value
                for key, value in review.items()
                if key not in {
                    "_workflowSnapshot",
                    "_workflowError",
                }
            },
            ensure_ascii=False,
            default=str,
        ),
    }

    mapped_fields = {
        "id",
        "reviewId",
        "name",
        "title",
        "description",
        "status",
        "result",
        "approvalStatus",
        "outcome",
        "createdAt",
        "updatedAt",
        "dueDate",
        "dueAt",
        "completedAt",
        "closedAt",
        "finishedAt",
        "createdBy",
        "updatedBy",
        "initiatedBy",
        "initiator",
        "initiatorId",
        "owner",
        "reviewOwner",
        "ownerId",
        "reviewers",
        "participants",
        "assignedReviewers",
        "approvers",
        "assignedApprovers",
        "workflow",
        "workflowId",
        "workflowName",
        "currentStep",
        "currentStepId",
        "currentStepName",
        "nextActionBy",
        "fileCount",
        "versionCount",
        "_workflowSnapshot",
        "_workflowError",
    }

    for key, value in review.items():
        if (
            key not in mapped_fields
            and key not in flattened
        ):
            flattened[key] = serialize_value(value)

    return flattened