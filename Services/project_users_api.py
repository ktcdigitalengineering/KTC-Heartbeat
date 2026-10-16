import requests


def normalize_project_id(project_id):
    return project_id[2:] if project_id.startswith("b.") else project_id


def get_project_users(project_id, access_token):
    project_id = normalize_project_id(project_id)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://developer.api.autodesk.com/construction/admin/v1/"
        f"projects/{project_id}/users"
    )

    user_map = {}

    while url:
        response = requests.get(url, headers=headers)


        if response.status_code != 200:
            raise Exception(
                f"Project Users API error {response.status_code}: "
                f"{response.text}"
            )

        data = response.json()
        users = data.get("results", [])

        """for i, user in enumerate(users):
            print("=" * 80)

            for key, value in user.items():
                print(f"{key} : {value}")

            if i == 0:
                break"""

        for user in users:
            user_name = (
                user.get("name")
                or user.get("displayName")
                or user.get("email")
            )

            autodesk_id = user.get("autodeskId")
            project_user_id = user.get("id")

            if autodesk_id and user_name:
                user_map[str(autodesk_id).strip()] = user_name

            if project_user_id and user_name:
                user_map[str(project_user_id).strip()] = user_name

        pagination = data.get("pagination", {})
        url = pagination.get("nextUrl")

    """print(f"Project users mapped: {len(user_map)}")
    print(user)"""

    return user_map