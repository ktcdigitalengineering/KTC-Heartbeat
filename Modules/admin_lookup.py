from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable


class AdminLookup:
    """
    Load Autodesk Data Connector Admin CSV files and build lookup maps.

    Supported lookups:
        - Users
        - Companies
        - Roles
        - Project users
        - Project companies
        - Project roles
        - User-to-company relationships
        - User-to-role relationships
    """

    FILE_NAMES = {
        "users": "admin_users",
        "companies": "admin_companies",
        "roles": "admin_roles",
        "project_users": "admin_project_users",
        "project_companies": "admin_project_companies",
        "project_roles": "admin_project_roles",
        "project_user_companies": "admin_project_user_companies",
        "project_user_roles": "admin_project_user_roles",
    }

    def __init__(
        self,
        data_connector_folder: str | Path,
        project_id: str | None = None,
    ) -> None:
        self.base_folder = Path(data_connector_folder)
        self.project_id = self.normalize_id(project_id)

        self.users: dict[str, dict[str, Any]] = {}
        self.companies: dict[str, dict[str, Any]] = {}
        self.roles: dict[str, dict[str, Any]] = {}

        self.project_users: dict[str, dict[str, Any]] = {}
        self.project_companies: dict[str, dict[str, Any]] = {}
        self.project_roles: dict[str, dict[str, Any]] = {}

        self.user_company_ids: dict[str, list[str]] = {}
        self.user_role_ids: dict[str, list[str]] = {}

        self._load_all()

    # ============================================================
    # GENERAL HELPERS
    # ============================================================

    @staticmethod
    def normalize_id(value: Any) -> str:
        """
        Convert IDs to a consistent string form.

        Examples:
            b.1234 -> 1234
            1234.0 -> 1234
            None   -> ""
        """

        if value is None:
            return ""

        text = str(value).strip()

        if not text:
            return ""

        if text.lower() in {"none", "nan", "null"}:
            return ""

        if text.startswith("b."):
            text = text[2:]

        if text.endswith(".0"):
            possible_number = text[:-2]

            if possible_number.isdigit():
                text = possible_number

        return text

    @staticmethod
    def first_value(
        row: dict[str, Any],
        possible_columns: Iterable[str],
    ) -> str:
        """
        Return the first populated value from possible columns.

        Column matching is case-insensitive.
        """

        lower_row = {
            str(key).strip().lower(): value
            for key, value in row.items()
        }

        for column in possible_columns:
            value = lower_row.get(str(column).lower())

            if value is None:
                continue

            text = str(value).strip()

            if text and text.lower() not in {
                "none",
                "nan",
                "null",
            }:
                return text

        return ""

    def find_csv_file(
        self,
        base_name: str,
    ) -> Path | None:
        """
        Locate a Data Connector CSV recursively and print
        which file is selected.
        """

        search_folder = self.base_folder

        if search_folder.is_file():
            search_folder = search_folder.parent

        print(f"\nSearching for: {base_name}")
        print(f"Search folder: {search_folder.resolve()}")

        if not search_folder.exists():
            print("ERROR: Lookup folder does not exist.")
            return None

        matches: list[Path] = []

        for file_path in search_folder.rglob("*.csv"):
            normalized_base = base_name.lower()
            normalized_stem = file_path.stem.lower()

            if normalized_base in normalized_stem:
                matches.append(file_path)

        if not matches:
            print(f"ERROR: No matching CSV found for {base_name}")
            print("CSV files available:")

            for file_path in search_folder.rglob("*.csv"):
                print(f"  {file_path.resolve()}")

            return None

        matches.sort(
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        print("Matching files:")

        for match in matches:
            print(f"  {match.resolve()}")

        selected_file = matches[0]

        print(f"Selected file: {selected_file.resolve()}")

        return selected_file

    @staticmethod
    def read_csv_file(
        file_path: Path | None,
    ) -> list[dict[str, Any]]:
        if file_path is None:
            return []

        encodings = (
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin-1",
        )

        last_error: Exception | None = None

        for encoding in encodings:
            try:
                with file_path.open(
                    mode="r",
                    encoding=encoding,
                    newline="",
                ) as csv_file:
                    reader = csv.DictReader(csv_file)
                    return list(reader)

            except UnicodeDecodeError as error:
                last_error = error

        if last_error:
            raise last_error

        return []

    # ============================================================
    # LOAD DATA
    # ============================================================

    def _load_all(self) -> None:
        print("\nLoading Data Connector Admin lookup files...")
        print(f"Lookup folder: {self.base_folder}")

        user_rows = self._load_rows("users")
        company_rows = self._load_rows("companies")
        role_rows = self._load_rows("roles")

        project_user_rows = self._load_rows("project_users")
        project_company_rows = self._load_rows(
            "project_companies"
        )
        project_role_rows = self._load_rows("project_roles")

        project_user_company_rows = self._load_rows(
            "project_user_companies"
        )
        project_user_role_rows = self._load_rows(
            "project_user_roles"
        )

        # Register every usable user identifier, including Autodesk ID.
        self.users = self._build_record_map(
            rows=user_rows,
            id_columns=(
                "id",
                "userId",
                "user_id",
                "autodeskId",
                "autodesk_id",
                "uid",
            ),
        )

        self.companies = self._build_record_map(
            rows=company_rows,
            id_columns=(
                "id",
                "companyId",
                "company_id",
                "accountId",
                "account_id",
            ),
        )

        self.roles = self._build_record_map(
            rows=role_rows,
            id_columns=(
                "id",
                "roleId",
                "role_id",
            ),
        )

        self.project_users = self._build_project_user_map(
            rows=self._filter_project_rows(project_user_rows)
        )

        # Issues use company_oxygen_id, such as 540712346.
        self.project_companies = self._build_project_company_map(
            rows=self._filter_project_rows(
                project_company_rows
            )
        )

        # Issues use role_oxygen_id, such as 535296459.
        self.project_roles = self._build_project_role_map(
            rows=self._filter_project_rows(project_role_rows)
        )

        self.user_company_ids = self._build_relationship_map(
            rows=self._filter_project_rows(
                project_user_company_rows
            ),
            source_columns=(
                "userId",
                "user_id",
                "projectUserId",
                "project_user_id",
            ),
            target_columns=(
                "companyId",
                "company_id",
            ),
        )

        self.user_role_ids = self._build_relationship_map(
            rows=self._filter_project_rows(
                project_user_role_rows
            ),
            source_columns=(
                "userId",
                "user_id",
                "projectUserId",
                "project_user_id",
            ),
            target_columns=(
                "roleId",
                "role_id",
            ),
        )

        print(
            "Admin lookup loaded: "
            f"{len(self.users)} user keys, "
            f"{len(self.companies)} company keys, "
            f"{len(self.roles)} role keys, "
            f"{len(self.project_companies)} project-company keys, "
            f"{len(self.project_roles)} project-role keys"
        )

    def _load_rows(
        self,
        file_key: str,
    ) -> list[dict[str, Any]]:
        base_name = self.FILE_NAMES[file_key]
        file_path = self.find_csv_file(base_name)

        if file_path is None:
            print(f"Lookup file not found: {base_name}")
            return []

        rows = self.read_csv_file(file_path)

        print(
            f"Loaded {len(rows)} row(s): "
            f"{file_path.name}"
        )

        return rows

    def _filter_project_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Keep rows belonging to the configured project when a project
        identifier column exists.
        """

        if not self.project_id:
            return rows

        filtered_rows: list[dict[str, Any]] = []
        project_column_found = False

        for row in rows:
            row_project_id = self.first_value(
                row,
                (
                    "projectId",
                    "project_id",
                    "bim360ProjectId",
                    "bim360_project_id",
                ),
            )

            if not row_project_id:
                continue

            project_column_found = True

            if (
                self.normalize_id(row_project_id)
                == self.project_id
            ):
                filtered_rows.append(row)

        if project_column_found:
            return filtered_rows

        # The export may already be project-specific.
        return rows

    def _build_record_map(
        self,
        rows: list[dict[str, Any]],
        id_columns: Iterable[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Register every populated identifier for every row.

        This is important because Autodesk may reference the same record
        by UUID, Autodesk ID, or another project-level identifier.
        """

        record_map: dict[str, dict[str, Any]] = {}

        for row in rows:
            for column in id_columns:
                record_id = self.normalize_id(
                    self.first_value(
                        row,
                        (column,),
                    )
                )

                if record_id:
                    record_map[record_id] = row

        return record_map

    def _build_relationship_map(
        self,
        rows: list[dict[str, Any]],
        source_columns: Iterable[str],
        target_columns: Iterable[str],
    ) -> dict[str, list[str]]:
        relationship_map: dict[str, list[str]] = {}

        for row in rows:
            source_id = self.normalize_id(
                self.first_value(
                    row,
                    source_columns,
                )
            )

            target_id = self.normalize_id(
                self.first_value(
                    row,
                    target_columns,
                )
            )

            if not source_id or not target_id:
                continue

            relationship_map.setdefault(source_id, [])

            if target_id not in relationship_map[source_id]:
                relationship_map[source_id].append(target_id)

        return relationship_map

    def _build_project_user_map(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Link admin_project_users.user_id to admin_users.id.
        """

        project_user_map: dict[str, dict[str, Any]] = {}

        for row in rows:
            user_id = self.normalize_id(
                self.first_value(
                    row,
                    (
                        "user_id",
                        "userId",
                    ),
                )
            )

            if not user_id:
                continue

            master_user_record = self.users.get(user_id)

            if master_user_record:
                combined_record = {
                    **row,
                    **master_user_record,
                }
            else:
                combined_record = row

            # Register all useful identifiers from the merged record.
            for column in (
                "user_id",
                "userId",
                "id",
                "autodesk_id",
                "autodeskId",
                "uid",
            ):
                lookup_id = self.normalize_id(
                    self.first_value(
                        combined_record,
                        (column,),
                    )
                )

                if lookup_id:
                    project_user_map[lookup_id] = combined_record

        return project_user_map

    def _build_project_company_map(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Link:
            admin_project_companies.company_oxygen_id
                -> admin_project_companies.company_id
                -> admin_companies.id
                -> company name
        """

        project_company_map: dict[str, dict[str, Any]] = {}

        for row in rows:
            master_company_id = self.normalize_id(
                self.first_value(
                    row,
                    (
                        "company_id",
                        "companyId",
                    ),
                )
            )

            master_company_record = self.companies.get(
                master_company_id
            )

            if master_company_record:
                combined_record = {
                    **row,
                    **master_company_record,
                }
            else:
                combined_record = row

            for column in (
                "company_oxygen_id",
                "company_id",
                "companyId",
                "id",
            ):
                lookup_id = self.normalize_id(
                    self.first_value(
                        row,
                        (column,),
                    )
                )

                if lookup_id:
                    project_company_map[lookup_id] = combined_record

            # Also register the master UUID after merging.
            if master_company_id:
                project_company_map[
                    master_company_id
                ] = combined_record

        return project_company_map

    def _build_project_role_map(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Register both role_oxygen_id and role_id.

        admin_project_roles.csv already contains the project role name.
        """

        project_role_map: dict[str, dict[str, Any]] = {}

        for row in rows:
            master_role_id = self.normalize_id(
                self.first_value(
                    row,
                    (
                        "role_id",
                        "roleId",
                    ),
                )
            )

            master_role_record = self.roles.get(master_role_id)

            # Keep the project role name if present.
            if master_role_record:
                combined_record = {
                    **master_role_record,
                    **row,
                }
            else:
                combined_record = row

            for column in (
                "role_oxygen_id",
                "role_id",
                "roleId",
                "id",
            ):
                lookup_id = self.normalize_id(
                    self.first_value(
                        row,
                        (column,),
                    )
                )

                if lookup_id:
                    project_role_map[lookup_id] = combined_record

            if master_role_id:
                project_role_map[master_role_id] = combined_record

        return project_role_map

    # ============================================================
    # USER LOOKUPS
    # ============================================================

    def get_user_record(
        self,
        user_id: Any,
    ) -> dict[str, Any] | None:
        normalized_id = self.normalize_id(user_id)

        if not normalized_id:
            return None

        return (
            self.users.get(normalized_id)
            or self.project_users.get(normalized_id)
        )

    def get_user_name(
        self,
        user_id: Any,
        default: str | None = None,
    ) -> str:
        normalized_id = self.normalize_id(user_id)

        if not normalized_id:
            return default or ""

        record = self.get_user_record(normalized_id)

        if not record:
            return default or normalized_id

        name = self.first_value(
            record,
            (
                "name",
                "display_name",
                "displayName",
                "full_name",
                "fullName",
            ),
        )

        if name:
            return name

        first_name = self.first_value(
            record,
            (
                "first_name",
                "firstName",
            ),
        )

        last_name = self.first_value(
            record,
            (
                "last_name",
                "lastName",
            ),
        )

        combined_name = " ".join(
            part
            for part in (
                first_name,
                last_name,
            )
            if part
        ).strip()

        if combined_name:
            return combined_name

        email = self.first_value(
            record,
            (
                "email",
                "email_address",
                "emailAddress",
            ),
        )

        return email or default or normalized_id

    def get_user_email(
        self,
        user_id: Any,
        default: str = "",
    ) -> str:
        record = self.get_user_record(user_id)

        if not record:
            return default

        return self.first_value(
            record,
            (
                "email",
                "emailAddress",
                "email_address",
            ),
        ) or default

    # ============================================================
    # COMPANY LOOKUPS
    # ============================================================

    def get_company_record(
        self,
        company_id: Any,
    ) -> dict[str, Any] | None:
        normalized_id = self.normalize_id(company_id)

        if not normalized_id:
            return None

        return (
            self.project_companies.get(normalized_id)
            or self.companies.get(normalized_id)
        )

    def get_company_name(
        self,
        company_id: Any,
        default: str | None = None,
    ) -> str:
        normalized_id = self.normalize_id(company_id)

        if not normalized_id:
            return default or ""

        record = self.get_company_record(normalized_id)

        if not record:
            return default or normalized_id

        name = self.first_value(
            record,
            (
                "name",
                "companyName",
                "company_name",
                "displayName",
                "display_name",
                "tradeName",
                "trade_name",
            ),
        )

        return name or default or normalized_id

    # ============================================================
    # ROLE LOOKUPS
    # ============================================================

    def get_role_record(
        self,
        role_id: Any,
    ) -> dict[str, Any] | None:
        normalized_id = self.normalize_id(role_id)

        if not normalized_id:
            return None

        return (
            self.project_roles.get(normalized_id)
            or self.roles.get(normalized_id)
        )

    def get_role_name(
        self,
        role_id: Any,
        default: str | None = None,
    ) -> str:
        normalized_id = self.normalize_id(role_id)

        if not normalized_id:
            return default or ""

        record = self.get_role_record(normalized_id)

        if not record:
            return default or normalized_id

        name = self.first_value(
            record,
            (
                "name",
                "roleName",
                "role_name",
                "displayName",
                "display_name",
            ),
        )

        return name or default or normalized_id

    # ============================================================
    # ASSIGNEE LOOKUP
    # ============================================================

    def resolve_assignee(
        self,
        assigned_to: Any,
        assigned_to_type: Any,
    ) -> str:
        """
        Resolve an Issue assignee based on assignedToType.
        """

        assignee_id = self.normalize_id(assigned_to)

        if not assignee_id:
            return ""

        assignee_type = str(
            assigned_to_type or ""
        ).strip().lower()

        if assignee_type in {
            "user",
            "users",
            "individual",
        }:
            return self.get_user_name(assignee_id)

        if assignee_type in {
            "company",
            "companies",
        }:
            return self.get_company_name(assignee_id)

        if assignee_type in {
            "role",
            "roles",
        }:
            return self.get_role_name(assignee_id)

        if self.get_user_record(assignee_id):
            return self.get_user_name(assignee_id)

        if self.get_company_record(assignee_id):
            return self.get_company_name(assignee_id)

        if self.get_role_record(assignee_id):
            return self.get_role_name(assignee_id)

        return assignee_id

    # ============================================================
    # USER RELATIONSHIPS
    # ============================================================

    def get_user_company_names(
        self,
        user_id: Any,
    ) -> list[str]:
        normalized_id = self.normalize_id(user_id)

        company_ids = self.user_company_ids.get(
            normalized_id,
            [],
        )

        return [
            self.get_company_name(company_id)
            for company_id in company_ids
        ]

    def get_user_role_names(
        self,
        user_id: Any,
    ) -> list[str]:
        normalized_id = self.normalize_id(user_id)

        role_ids = self.user_role_ids.get(
            normalized_id,
            [],
        )

        return [
            self.get_role_name(role_id)
            for role_id in role_ids
        ]