import os
import requests


def create_storage(project_id, folder_id, file_name, access_token):
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/storage"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.api+json"
    }

    payload = {
        "jsonapi": {
            "version": "1.0"
        },
        "data": {
            "type": "objects",
            "attributes": {
                "name": file_name
            },
            "relationships": {
                "target": {
                    "data": {
                        "type": "folders",
                        "id": folder_id
                    }
                }
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [200, 201]:
        raise Exception(f"Create storage error {response.status_code}: {response.text}")

    data = response.json()
    return data["data"]["id"]


def upload_file_to_storage(storage_id, file_path, access_token):
    import os
    import requests

    # storage_id looks like:
    # urn:adsk.objects:os.object:wip.dm.prod/xxxx.csv
    object_id = storage_id.split("/")[-1]
    bucket_key = "wip.dm.prod"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Get signed S3 upload URL
    signed_url_endpoint = (
        f"https://developer.api.autodesk.com/oss/v2/"
        f"buckets/{bucket_key}/objects/{object_id}/signeds3upload"
        f"?parts=1"
    )

    signed_response = requests.get(
        signed_url_endpoint,
        headers=headers
    )

    if signed_response.status_code != 200:
        raise Exception(
            f"Get signed upload URL error {signed_response.status_code}: "
            f"{signed_response.text}"
        )

    signed_data = signed_response.json()

    upload_key = signed_data["uploadKey"]
    upload_url = signed_data["urls"][0]

    # Step 2: Upload file directly to signed S3 URL
    with open(file_path, "rb") as file:
        upload_response = requests.put(
            upload_url,
            data=file
        )

    if upload_response.status_code not in [200, 201]:
        raise Exception(
            f"S3 upload error {upload_response.status_code}: "
            f"{upload_response.text}"
        )

    # Step 3: Complete S3 upload
    complete_endpoint = (
        f"https://developer.api.autodesk.com/oss/v2/"
        f"buckets/{bucket_key}/objects/{object_id}/signeds3upload"
    )

    complete_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    complete_payload = {
        "uploadKey": upload_key
    }

    complete_response = requests.post(
        complete_endpoint,
        headers=complete_headers,
        json=complete_payload
    )

    if complete_response.status_code not in [200, 201]:
        raise Exception(
            f"Complete S3 upload error {complete_response.status_code}: "
            f"{complete_response.text}"
        )


def create_item(project_id, folder_id, storage_id, file_name, access_token):
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/items"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.api+json"
    }

    payload = {
        "jsonapi": {
            "version": "1.0"
        },
        "data": {
            "type": "items",
            "attributes": {
                "displayName": file_name,
                "extension": {
                    "type": "items:autodesk.bim360:File",
                    "version": "1.0"
                }
            },
            "relationships": {
                "tip": {
                    "data": {
                        "type": "versions",
                        "id": "1"
                    }
                },
                "parent": {
                    "data": {
                        "type": "folders",
                        "id": folder_id
                    }
                }
            }
        },
        "included": [
            {
                "type": "versions",
                "id": "1",
                "attributes": {
                    "name": file_name,
                    "extension": {
                        "type": "versions:autodesk.bim360:File",
                        "version": "1.0"
                    }
                },
                "relationships": {
                    "storage": {
                        "data": {
                            "type": "objects",
                            "id": storage_id
                        }
                    }
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [200, 201]:
        raise Exception(f"Create item error {response.status_code}: {response.text}")

    return response.json()


def upload_csv_to_acc(project_id, folder_id, file_path, access_token):
    file_name = os.path.basename(file_path)

    existing_item = find_file_in_folder(
        project_id,
        folder_id,
        file_name,
        access_token
    )

    storage_id = create_storage(
        project_id,
        folder_id,
        file_name,
        access_token
    )

    upload_file_to_storage(
        storage_id,
        file_path,
        access_token
    )

    if existing_item:
        item_id = existing_item["id"]

        print(f"Existing file found. Creating new version: {file_name}")

        result = create_new_version(
            project_id,
            item_id,
            storage_id,
            file_name,
            access_token
        )

    else:
        print(f"No existing file found. Creating new item: {file_name}")

        result = create_item(
            project_id,
            folder_id,
            storage_id,
            file_name,
            access_token
        )

    return result

def find_file_in_folder(project_id, folder_id, file_name, access_token):
    url = (
        f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/"
        f"folders/{folder_id}/contents"
    )

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    while url:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(
                f"Find file error {response.status_code}: {response.text}"
            )

        data = response.json()

        for item in data.get("data", []):
            if item.get("type") == "items":
                display_name = item.get("attributes", {}).get("displayName")

                if display_name == file_name:
                    return item

        links = data.get("links", {})
        next_link = links.get("next", {})
        url = next_link.get("href")

    return None

def create_new_version(project_id, item_id, storage_id, file_name, access_token):
    url = f"https://developer.api.autodesk.com/data/v1/projects/{project_id}/versions"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.api+json"
    }

    payload = {
        "jsonapi": {
            "version": "1.0"
        },
        "data": {
            "type": "versions",
            "attributes": {
                "name": file_name,
                "extension": {
                    "type": "versions:autodesk.bim360:File",
                    "version": "1.0"
                }
            },
            "relationships": {
                "item": {
                    "data": {
                        "type": "items",
                        "id": item_id
                    }
                },
                "storage": {
                    "data": {
                        "type": "objects",
                        "id": storage_id
                    }
                }
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [200, 201]:
        raise Exception(
            f"Create version error {response.status_code}: {response.text}"
        )

    return response.json()