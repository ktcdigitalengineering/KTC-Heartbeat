from config import PROJECTS
from Modules.admin_lookup import AdminLookup


def main() -> None:
    tested_projects = 0

    for project in PROJECTS:
        project_name = project.get("name", "Unnamed Project")
        project_id = project.get("project_id", "")

        data_connector_enabled = (
            project
            .get("exports", {})
            .get("data_connector", False)
        )

        if not data_connector_enabled:
            print("\n" + "=" * 70)
            print(f"SKIPPED: {project_name}")
            print("Reason: data_connector export is disabled")
            print("=" * 70)
            continue

        lookup_folder = (
            project
            .get("output_files", {})
            .get("data_connector")
        )

        if not lookup_folder:
            print("\n" + "=" * 70)
            print(f"SKIPPED: {project_name}")
            print(
                "Reason: output_files[data_connector] "
                "is not configured"
            )
            print("=" * 70)
            continue

        tested_projects += 1

        print("\n" + "=" * 70)
        print(f"TESTING ADMIN LOOKUP: {project_name}")
        print(f"PROJECT ID: {project_id}")
        print(f"LOOKUP FOLDER: {lookup_folder}")
        print("=" * 70)

        try:
            lookup = AdminLookup(
                data_connector_folder=lookup_folder,
                project_id=project_id,
            )

        except Exception as error:
            print(f"ADMIN LOOKUP FAILED: {error}")
            continue

        print("\nLookup counts:")
        print(
            f"Master companies: "
            f"{len(lookup.companies)}"
        )
        print(
            f"Project companies: "
            f"{len(lookup.project_companies)}"
        )
        print(
            f"Master users: "
            f"{len(lookup.users)}"
        )
        print(
            f"Project users: "
            f"{len(lookup.project_users)}"
        )
        print(
            f"Master roles: "
            f"{len(lookup.roles)}"
        )
        print(
            f"Project roles: "
            f"{len(lookup.project_roles)}"
        )

        print("\nSample project companies:")

        company_keys = list(
            lookup.project_companies.keys()
        )

        if company_keys:
            for company_id in company_keys[:10]:
                print(
                    f"{company_id} -> "
                    f"{lookup.get_company_name(company_id)}"
                )
        else:
            print("No project companies loaded.")

        print("\nSample project roles:")

        role_keys = list(
            lookup.project_roles.keys()
        )

        if role_keys:
            for role_id in role_keys[:10]:
                print(
                    f"{role_id} -> "
                    f"{lookup.get_role_name(role_id)}"
                )
        else:
            print("No project roles loaded.")

        print("\nSample project users:")

        user_keys = list(
            lookup.project_users.keys()
        )

        if user_keys:
            for user_id in user_keys[:10]:
                print(
                    f"{user_id} -> "
                    f"{lookup.get_user_name(user_id)}"
                )
        else:
            print("No project users loaded.")

        print("\nLookup status:")

        if lookup.project_companies:
            print("Project company lookup: OK")
        else:
            print("Project company lookup: EMPTY")

        if lookup.project_roles:
            print("Project role lookup: OK")
        else:
            print("Project role lookup: EMPTY")

        if lookup.project_users:
            print("Project user lookup: OK")
        else:
            print("Project user lookup: EMPTY")

    print("\n" + "=" * 70)
    print(f"ADMIN LOOKUP TEST COMPLETED")
    print(f"Projects tested: {tested_projects}")
    print("=" * 70)


if __name__ == "__main__":
    main()