-- ==========================================================
-- PostgreSQL schema for the ACC export CSVs
-- ==========================================================
--
-- One table per export type, mirroring what Modules/csv_export.py writes.
--
-- Column names are the CSV headers converted camelCase -> snake_case
-- (createdByName -> created_by_name, answeredAtV2 -> answered_at_v2,
-- revision_itemId -> revision_item_id). There are no exceptions, so a
-- loader can map headers mechanically.
--
-- Every table also has:
--   project_id  the ACC project, WITHOUT the "b." prefix used in config.py
--   extra       every CSV column that has no fixed column here, keyed by the
--               original CSV header. This is where per-project custom
--               attributes ("Meeting No.", "KTC Volume", ...) land, along
--               with any field APS starts returning later.
--   loaded_at   when the row was last written
--
-- Type notes:
--   * Record IDs are uuid. User, company and role IDs are text: they are
--     Autodesk IDs or numeric role/company IDs depending on the *Type field.
--   * Empty CSV cells should be loaded as NULL.
--   * jsonb columns hold the nested values the exporters serialize to a
--     string. Issues, RFIs, reviews and submittal revisions write real JSON.
--     Assets and submittals write Python repr (str(value), single quotes),
--     so those need ast.literal_eval before they can be inserted as jsonb.
--
-- Safe to re-run: everything is CREATE ... IF NOT EXISTS.

CREATE SCHEMA IF NOT EXISTS acc_export;

SET search_path TO acc_export;


-- ==========================================================
-- PROJECTS
-- ==========================================================

CREATE TABLE IF NOT EXISTS projects (
    project_id      uuid        PRIMARY KEY,
    name            text        NOT NULL UNIQUE,
    account_id      uuid,
    loaded_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE projects IS
    'One row per entry in config.PROJECTS. project_id has no "b." prefix.';


-- ==========================================================
-- ASSETS
-- ==========================================================

CREATE TABLE IF NOT EXISTS assets (
    id                  uuid        PRIMARY KEY,
    project_id          uuid        NOT NULL REFERENCES projects (project_id),

    client_asset_id     text,
    description         text,
    version             integer,
    is_active           boolean,

    category_id         text,
    category_level1     text,
    category_level2     text,

    status_id           uuid,
    status              text,

    location_id         uuid,

    created_at          timestamptz,
    created_by          text,
    updated_at          timestamptz,
    updated_by          text,

    extra               jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS assets_project_idx  ON assets (project_id);
CREATE INDEX IF NOT EXISTS assets_status_idx   ON assets (project_id, status);
CREATE INDEX IF NOT EXISTS assets_category_idx ON assets (project_id, category_level1, category_level2);
CREATE INDEX IF NOT EXISTS assets_extra_idx    ON assets USING gin (extra);


-- ==========================================================
-- SUBMITTALS
-- ==========================================================

CREATE TABLE IF NOT EXISTS submittals (
    id                                  uuid        PRIMARY KEY,
    project_id                          uuid        NOT NULL REFERENCES projects (project_id),

    identifier                          integer,
    custom_identifier                   text,
    custom_identifier_human_readable    text,
    title                               text,
    description                         text,
    priority                            text,
    revision                            integer,

    type_id                             uuid,
    item_type                           text,

    spec_id                             uuid,
    spec_identifier                     text,
    spec_title                          text,
    subsection                          text,

    state_id                            text,
    status_id                           text,
    status                              text,

    ball_in_court                       jsonb,
    ball_in_court_users                 jsonb,
    ball_in_court_user_names            text,
    ball_in_court_companies             jsonb,
    ball_in_court_roles                 jsonb,
    ball_in_court_type                  text,

    manager                             text,
    manager_name                        text,
    manager_type                        text,
    subcontractor                       text,
    subcontractor_name                  text,
    subcontractor_type                  text,
    watchers                            jsonb,

    due_date                            date,
    required_on_job_date                date,
    lead_time                           numeric,
    required_date                       date,
    required_approval_date              date,

    submitter_due_date                  date,
    sent_to_submitter                   timestamptz,
    received_from_submitter             timestamptz,
    submitted_by                        text,
    submitted_by_name                   text,

    manager_due_date                    date,
    sent_to_review                      timestamptz,
    sent_to_review_by                   text,
    sent_to_review_by_name              text,
    received_from_review                timestamptz,

    published_date                      timestamptz,
    published_by                        text,

    response_id                         uuid,
    response                            text,
    response_comment                    text,
    responded_at                        timestamptz,
    responded_by                        text,
    responded_by_name                   text,

    package_id                          uuid,
    package                             text,
    package_identifier                  text,
    package_title                       text,
    package_spec_identifier             text,

    folder_urn                          text,
    revisions_folders_urns              jsonb,
    current_evaluation_id               uuid,

    permitted_actions                   jsonb,
    custom_attributes                   jsonb,

    created_at                          timestamptz,
    created_by                          text,
    created_by_name                     text,
    updated_at                          timestamptz,
    updated_by                          text,
    updated_by_name                     text,

    extra                               jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at                           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS submittals_project_idx    ON submittals (project_id);
CREATE INDEX IF NOT EXISTS submittals_status_idx     ON submittals (project_id, status);
CREATE INDEX IF NOT EXISTS submittals_package_idx    ON submittals (package_id);
CREATE INDEX IF NOT EXISTS submittals_updated_at_idx ON submittals (updated_at);


-- ==========================================================
-- SUBMITTAL REVISIONS
-- ==========================================================
--
-- The Submittals API returns no revision ID, so revision_id is always empty
-- and the key is (submittal_id, revision_number).
--
-- flatten_submittal_revision writes revision 0 as an empty cell
-- (revision.get("revision") or ... treats 0 as missing). Load a blank
-- revisionNumber as 0.
--
-- Naming differs from the submittals table: here submitted_by, created_by,
-- updated_by, manager and ball_in_court hold the resolved NAME and the
-- *_id sibling holds the ID. The revision_* columns are the raw API fields.

CREATE TABLE IF NOT EXISTS submittal_revisions (
    project_id                          uuid        NOT NULL REFERENCES projects (project_id),
    submittal_id                        uuid        NOT NULL REFERENCES submittals (id) ON DELETE CASCADE,
    revision_number                     integer     NOT NULL DEFAULT 0,
    revision_id                         text,

    identifier                          integer,
    title                               text,

    status_id                           text,
    status                              text,

    response_id                         uuid,
    response                            text,
    response_comment                    text,

    item_type_id                        text,
    item_type                           text,
    package_id                          uuid,
    package                             text,
    spec_section_id                     text,
    spec_section                        text,

    created_by_id                       text,
    created_by                          text,
    updated_by_id                       text,
    updated_by                          text,
    submitted_by_id                     text,
    submitted_by                        text,
    manager_id                          text,
    manager                             text,
    ball_in_court_id                    text,
    ball_in_court                       text,

    created_at                          timestamptz,
    updated_at                          timestamptz,
    submitted_at                        timestamptz,
    due_date                            date,
    responded_at                        timestamptz,

    revision_item_id                    uuid,
    revision_manager                    text,
    revision_manager_type               text,
    revision_subcontractor              text,
    revision_subcontractor_type         text,
    revision_sent_to_submitter          timestamptz,
    revision_submitter_due_date         date,
    revision_received_from_submitter    timestamptz,
    revision_sent_to_review             timestamptz,
    revision_sent_to_review_by          text,
    revision_manager_due_date           date,
    revision_reviewer_due_date          date,
    revision_received_from_review       timestamptz,
    revision_responded_by               text,
    revision_published_date             timestamptz,
    revision_published_by               text,
    revision_steps                      jsonb,

    extra                               jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at                           timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (submittal_id, revision_number)
);

CREATE INDEX IF NOT EXISTS submittal_revisions_project_idx ON submittal_revisions (project_id);


-- ==========================================================
-- RFIS
-- ==========================================================
--
-- custom_attributes is the raw list the API returns. The decoded,
-- named values (one CSV column per attribute) go into extra.

CREATE TABLE IF NOT EXISTS rfis (
    id                                      uuid        PRIMARY KEY,
    project_id                              uuid        NOT NULL REFERENCES projects (project_id),

    custom_identifier                       text,
    title                                   text,
    question                                text,
    suggested_answer                        text,
    status                                  text,
    previous_status                         text,
    priority                                text,
    workflow_type                           text,
    rfi_type_id                             uuid,
    reference                               text,
    discipline                              jsonb,
    category                                jsonb,
    cost_impact                             text,
    schedule_impact                         text,

    due_date                                timestamptz,
    opened_at                               timestamptz,

    assigned_to                             jsonb,
    assigned_to_name                        text,
    manager_id                              text,
    manager_id_name                         text,
    reviewers                               jsonb,
    reviewers_names                         text,
    co_reviewers                            jsonb,
    co_reviewers_names                      text,
    optional_reviewers                      jsonb,
    architects                              jsonb,
    watchers                                jsonb,
    watchers_names                          text,
    max_assignees                           integer,

    responses                               jsonb,
    draft_responses                         jsonb,
    answered_at                             timestamptz,
    answered_by                             text,
    answered_at_v2                          timestamptz,
    answered_by_v2                          text,

    official_response                       text,
    official_response_status                text,
    official_response_actors                jsonb,
    official_response_edit_by_manager_state boolean,
    responded_at                            timestamptz,
    responded_by                            text,
    responded_by_name                       text,

    closed_at                               timestamptz,
    closed_by                               text,
    closed_by_name                          text,

    locations                               jsonb,
    location_description                    text,
    virtual_folder_urn                      text,

    comments_count                          integer,
    attachments_count                       integer,

    platform                                text,
    bridged_source                          boolean,
    bridged_target                          boolean,
    bridge_sync_outdated                    boolean,
    sync_version                            integer,
    hash                                    text,

    permitted_actions                       jsonb,
    custom_attributes                       jsonb,

    created_at                              timestamptz,
    created_by                              text,
    created_by_name                         text,
    updated_at                              timestamptz,
    updated_by                              text,
    updated_by_name                         text,

    extra                                   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at                               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rfis_project_idx    ON rfis (project_id);
CREATE INDEX IF NOT EXISTS rfis_status_idx     ON rfis (project_id, status);
CREATE INDEX IF NOT EXISTS rfis_due_date_idx   ON rfis (due_date);
CREATE INDEX IF NOT EXISTS rfis_updated_at_idx ON rfis (updated_at);


-- ==========================================================
-- ISSUES
-- ==========================================================
--
-- assigned_to is a user, company or role ID depending on assigned_to_type;
-- assigned_to_name is what AdminLookup.resolve_assignee returned.

CREATE TABLE IF NOT EXISTS issues (
    id                      uuid        PRIMARY KEY,
    project_id              uuid        NOT NULL REFERENCES projects (project_id),

    container_id            uuid,
    display_id              integer,
    title                   text,
    description             text,
    status                  text,

    issue_type_id           uuid,
    issue_subtype_id        uuid,
    issue_type              text,
    issue_subtype           text,
    issue_template_id       text,

    root_cause_id           uuid,
    root_cause_category     text,
    root_cause              text,

    assigned_to             text,
    assigned_to_name        text,
    assigned_to_type        text,
    owner_id                text,

    due_date                date,
    start_date              date,

    location_id             uuid,
    location_details        text,
    gps_coordinates         jsonb,
    placements              jsonb,

    snapshot_urn            text,
    snapshot_has_markups    boolean,
    linked_documents        jsonb,
    links                   jsonb,

    official_response       jsonb,
    published               boolean,
    deleted                 boolean,
    comment_count           integer,
    attachment_count        integer,

    watchers                jsonb,
    watcher_names           text,
    watcher_objects         jsonb,
    watcher_object_names    text,

    permitted_attributes    jsonb,
    permitted_actions       jsonb,
    permitted_statuses      jsonb,

    opened_at               timestamptz,
    opened_by               text,
    opened_by_name          text,
    closed_at               timestamptz,
    closed_by               text,
    closed_by_name          text,
    created_at              timestamptz,
    created_by              text,
    created_by_name         text,
    updated_at              timestamptz,
    updated_by              text,
    updated_by_name         text,

    extra                   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at               timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS issues_project_idx     ON issues (project_id);
CREATE INDEX IF NOT EXISTS issues_display_id_idx  ON issues (project_id, display_id);
CREATE INDEX IF NOT EXISTS issues_status_idx      ON issues (project_id, status);
CREATE INDEX IF NOT EXISTS issues_subtype_idx     ON issues (issue_subtype_id);
CREATE INDEX IF NOT EXISTS issues_assigned_to_idx ON issues (assigned_to);
CREATE INDEX IF NOT EXISTS issues_due_date_idx    ON issues (due_date);
CREATE INDEX IF NOT EXISTS issues_updated_at_idx  ON issues (updated_at);
CREATE INDEX IF NOT EXISTS issues_extra_idx       ON issues USING gin (extra);


-- ==========================================================
-- REVIEWS
-- ==========================================================
--
-- The *_ids / *_names / workflow_step_* columns are delimited strings, as
-- flatten_review writes them. raw_review_json keeps the full API record.

CREATE TABLE IF NOT EXISTS reviews (
    review_id                       uuid        PRIMARY KEY,
    project_id                      uuid        NOT NULL REFERENCES projects (project_id),

    sequence_id                     integer,
    name                            text,
    description                     text,
    status                          text,
    result                          text,
    file_count                      integer,

    due_date                        timestamptz,
    completed_at                    timestamptz,

    initiated_by                    text,
    initiated_by_name               text,
    owner_id                        text,
    owner_name                      text,
    reviewer_ids                    text,
    reviewer_names                  text,
    approver_ids                    text,
    approver_names                  text,

    workflow_id                     uuid,
    workflow_name                   text,
    workflow_step_ids               text,
    workflow_step_names             text,
    workflow_step_types             text,
    workflow_candidate_ids          text,
    workflow_candidate_names        text,
    workflow_error                  text,

    current_step_id                 text,
    current_step_name               text,
    current_step_due_date           timestamptz,

    next_action_claimed_by_ids      text,
    next_action_claimed_by_names    text,
    next_action_user_ids            text,
    next_action_user_names          text,
    next_action_role_ids            text,
    next_action_role_names          text,
    next_action_company_ids         text,
    next_action_company_names       text,

    approved_by                     jsonb,
    approved_at                     timestamptz,
    archived                        boolean,
    archived_by                     text,
    archived_at                     timestamptz,

    created_at                      timestamptz,
    created_by                      text,
    created_by_name                 text,
    updated_at                      timestamptz,
    updated_by                      text,
    updated_by_name                 text,

    raw_review_json                 jsonb,

    extra                           jsonb       NOT NULL DEFAULT '{}'::jsonb,
    loaded_at                       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reviews_project_idx     ON reviews (project_id);
CREATE INDEX IF NOT EXISTS reviews_status_idx      ON reviews (project_id, status);
CREATE INDEX IF NOT EXISTS reviews_workflow_idx    ON reviews (workflow_id);
CREATE INDEX IF NOT EXISTS reviews_updated_at_idx  ON reviews (updated_at);
