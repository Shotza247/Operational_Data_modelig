from pathlib import Path

import pandas as pd


CLEANING_OUTPUT_DIR = Path("standardized_cleaned_data")
RULE_CATALOGUE_PATH = Path("data_inventory/data_quality_rule_catalogue.csv")
EXCEPTION_CANDIDATES_PATH = CLEANING_OUTPUT_DIR / "exception_candidates.csv"
TRANSFORMATION_ISSUES_PATH = (
    CLEANING_OUTPUT_DIR
    / "transformation_logging"
    / "transformation_log_validation_issues.csv"
)
RECONCILIATION_FINDINGS_PATH = (
    CLEANING_OUTPUT_DIR
    / "reconciliation"
    / "reconciliation_findings.csv"
)
OUTPUT_DIR = CLEANING_OUTPUT_DIR / "exception_register"

SEVERITY_RANK = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
}

STATUS_RANK = {
    "REVIEW_REQUIRED": 1,
    "UNRESOLVED": 2,
    "REJECT": 3,
    "AUTO_CORRECT": 4,
    "AUTO_ACCEPT": 5,
}

REGISTER_COLUMNS = [
    "Register_ID",
    "Exception_ID",
    "Dataset",
    "Source_Row_Index",
    "Source_Row_Number",
    "Record_ID",
    "Column",
    "Issue_Type",
    "Current_Value",
    "Rule_ID",
    "Rule_Type",
    "Valid_Condition",
    "Rule_Action",
    "Rule_Reason",
    "Severity",
    "Severity_Rank",
    "Status",
    "Review_Priority",
    "Recommended_Action",
    "Review_Owner",
    "Review_Decision",
    "Resolution_Value",
    "Resolution_Notes",
    "Include_In_Trusted_Data",
    "Requires_Source_Review",
    "Created_From",
]


def load_exception_candidates(path=EXCEPTION_CANDIDATES_PATH):
    return pd.read_csv(path)


def load_rule_catalogue(path=RULE_CATALOGUE_PATH):
    return pd.read_csv(path)


def load_transformation_issues(path=TRANSFORMATION_ISSUES_PATH):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def load_reconciliation_findings(path=RECONCILIATION_FINDINGS_PATH):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def resolve_frame(value, default_path, loader):
    if isinstance(value, pd.DataFrame):
        return value.copy()

    if value is None:
        return loader(default_path)

    return loader(value)


def normalise_exception_candidates(exception_candidates_df):
    exceptions = exception_candidates_df.copy()
    exceptions["Created_From"] = "exception_candidates.csv"

    rename_map = {
        "Value": "Current_Value",
        "Status": "Status",
    }
    exceptions = exceptions.rename(columns=rename_map)

    return exceptions


def normalise_transformation_issues(transformation_issues_df):
    if transformation_issues_df.empty:
        return pd.DataFrame(columns=[
            "Exception_ID",
            "Dataset",
            "Source_Row_Index",
            "Source_Row_Number",
            "Record_ID",
            "Column",
            "Issue_Type",
            "Current_Value",
            "Rule_ID",
            "Severity",
            "Recommended_Action",
            "Status",
            "Created_From",
        ])

    issues = transformation_issues_df.copy()
    issues["Exception_ID"] = [
        f"TRN-ISSUE-{row_number:05d}"
        for row_number in range(1, len(issues) + 1)
    ]
    issues["Source_Row_Index"] = ""
    issues["Source_Row_Number"] = ""
    issues["Current_Value"] = issues.get("Details", "")
    issues["Recommended_Action"] = "Review transformation log evidence"
    issues["Status"] = "REVIEW_REQUIRED"
    issues["Created_From"] = "transformation_log_validation_issues.csv"

    expected_columns = [
        "Exception_ID",
        "Dataset",
        "Source_Row_Index",
        "Source_Row_Number",
        "Record_ID",
        "Column",
        "Issue_Type",
        "Current_Value",
        "Rule_ID",
        "Severity",
        "Recommended_Action",
        "Status",
        "Created_From",
    ]

    for column in expected_columns:
        if column not in issues.columns:
            issues[column] = ""

    return issues[expected_columns]


def normalise_reconciliation_findings(reconciliation_findings_df):
    if reconciliation_findings_df.empty:
        return pd.DataFrame(columns=[
            "Exception_ID",
            "Dataset",
            "Source_Row_Index",
            "Source_Row_Number",
            "Record_ID",
            "Column",
            "Issue_Type",
            "Current_Value",
            "Rule_ID",
            "Severity",
            "Recommended_Action",
            "Status",
            "Created_From",
        ])

    findings = reconciliation_findings_df.copy()
    findings["Exception_ID"] = findings["Reconciliation_ID"]
    findings["Rule_ID"] = "RECONCILIATION-CHECK"
    findings["Created_From"] = "reconciliation_findings.csv"

    expected_columns = [
        "Exception_ID",
        "Dataset",
        "Source_Row_Index",
        "Source_Row_Number",
        "Record_ID",
        "Column",
        "Issue_Type",
        "Current_Value",
        "Rule_ID",
        "Severity",
        "Recommended_Action",
        "Status",
        "Created_From",
    ]

    for column in expected_columns:
        if column not in findings.columns:
            findings[column] = ""

    return findings[expected_columns]


def enrich_with_rule_catalogue(exceptions_df, rule_catalogue_df):
    rule_columns = [
        "Rule_ID",
        "Rule_Type",
        "Valid_Condition",
        "Action",
        "Reason",
    ]
    rules = rule_catalogue_df[rule_columns].drop_duplicates("Rule_ID")

    enriched = exceptions_df.merge(
        rules,
        on="Rule_ID",
        how="left",
    )

    enriched = enriched.rename(
        columns={
            "Action": "Rule_Action",
            "Reason": "Rule_Reason",
        }
    )
    reconciliation_mask = enriched["Rule_ID"] == "RECONCILIATION-CHECK"
    enriched.loc[reconciliation_mask, "Rule_Type"] = "Reconciliation"
    enriched.loc[
        reconciliation_mask,
        "Valid_Condition",
    ] = "Cross-dataset records should agree at shared operator, equipment, and event grains"
    enriched.loc[
        reconciliation_mask,
        "Rule_Action",
    ] = "Flag cross-dataset contradictions for source review"
    enriched.loc[
        reconciliation_mask,
        "Rule_Reason",
    ] = "Reconciliation checks identify contradictions that cleaning alone cannot resolve"

    return enriched


def classify_priority(row):
    severity = row.get("Severity", "")
    issue_type = str(row.get("Issue_Type", "")).lower()

    if severity == "Critical":
        return "P1"

    if severity == "High":
        return "P2"

    if "temporal" in issue_type or "unparseable date" in issue_type:
        return "P2"

    return "P3"


def should_include_in_trusted_data(row):
    severity = row.get("Severity", "")
    issue_type = str(row.get("Issue_Type", "")).lower()

    if severity == "Critical":
        return "No - unresolved critical exception"

    if "temporal contradiction" in issue_type:
        return "No - unresolved contradiction"

    if "unparseable date" in issue_type:
        return "Review before time-based analysis"

    return "Yes with documented caveat"


def requires_source_review(row):
    severity = row.get("Severity", "")
    issue_type = str(row.get("Issue_Type", "")).lower()

    return severity in {"Critical", "High"} or "contradiction" in issue_type


def assign_review_owner(row):
    issue_type = str(row.get("Issue_Type", "")).lower()
    column = str(row.get("Column", "")).lower()

    if "date" in column or "time" in column or "temporal" in issue_type:
        return "Operations data steward"

    if "numeric" in issue_type or "score" in issue_type or "percentage" in issue_type:
        return "Domain subject-matter reviewer"

    return "Data quality reviewer"


def build_exception_register(
    exception_candidates_df,
    rule_catalogue_df,
    transformation_issues_df=None,
    reconciliation_findings_df=None,
):
    exception_candidates = normalise_exception_candidates(exception_candidates_df)
    transformation_issues = normalise_transformation_issues(
        transformation_issues_df
        if transformation_issues_df is not None
        else pd.DataFrame()
    )
    reconciliation_findings = normalise_reconciliation_findings(
        reconciliation_findings_df
        if reconciliation_findings_df is not None
        else pd.DataFrame()
    )

    combined = pd.concat(
        [exception_candidates, transformation_issues, reconciliation_findings],
        ignore_index=True,
        sort=False,
    )
    combined = enrich_with_rule_catalogue(combined, rule_catalogue_df)

    combined["Severity_Rank"] = combined["Severity"].map(SEVERITY_RANK).fillna(99).astype(int)
    combined["Status"] = combined["Status"].fillna("REVIEW_REQUIRED")
    combined["Status_Rank"] = combined["Status"].map(STATUS_RANK).fillna(99).astype(int)
    combined["Review_Priority"] = combined.apply(classify_priority, axis=1)
    combined["Review_Owner"] = combined.apply(assign_review_owner, axis=1)
    combined["Review_Decision"] = ""
    combined["Resolution_Value"] = ""
    combined["Resolution_Notes"] = ""
    combined["Include_In_Trusted_Data"] = combined.apply(
        should_include_in_trusted_data,
        axis=1,
    )
    combined["Requires_Source_Review"] = combined.apply(
        requires_source_review,
        axis=1,
    )

    combined = combined.sort_values(
        ["Severity_Rank", "Status_Rank", "Dataset", "Source_Row_Number", "Column"],
        kind="stable",
    ).reset_index(drop=True)
    combined["Register_ID"] = [
        f"REG-{row_number:05d}" for row_number in range(1, len(combined) + 1)
    ]

    for column in REGISTER_COLUMNS:
        if column not in combined.columns:
            combined[column] = ""

    return combined[REGISTER_COLUMNS]


def summarise_exception_register(exception_register_df):
    total_exceptions = len(exception_register_df)
    source_review_count = int(exception_register_df["Requires_Source_Review"].sum())

    return pd.DataFrame(
        [
            {
                "Metric": "Total exceptions",
                "Value": total_exceptions,
            },
            {
                "Metric": "Critical exceptions",
                "Value": int((exception_register_df["Severity"] == "Critical").sum()),
            },
            {
                "Metric": "High exceptions",
                "Value": int((exception_register_df["Severity"] == "High").sum()),
            },
            {
                "Metric": "Review required",
                "Value": int((exception_register_df["Status"] == "REVIEW_REQUIRED").sum()),
            },
            {
                "Metric": "Requires source review",
                "Value": source_review_count,
            },
            {
                "Metric": "Excluded from trusted data until resolved",
                "Value": int(
                    exception_register_df["Include_In_Trusted_Data"]
                    .astype(str)
                    .str.startswith("No")
                    .sum()
                ),
            },
        ]
    )


def summarise_by_dataset(exception_register_df):
    return (
        exception_register_df.groupby("Dataset")
        .agg(
            Exception_Count=("Register_ID", "count"),
            Critical_Count=("Severity", lambda values: int((values == "Critical").sum())),
            High_Count=("Severity", lambda values: int((values == "High").sum())),
            Source_Review_Count=("Requires_Source_Review", "sum"),
            Affected_Record_Count=("Record_ID", "nunique"),
            Affected_Column_Count=("Column", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["Critical_Count", "High_Count", "Exception_Count"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )


def summarise_by_issue_type(exception_register_df):
    return (
        exception_register_df.groupby(["Issue_Type", "Severity"])
        .agg(
            Exception_Count=("Register_ID", "count"),
            Dataset_Count=("Dataset", "nunique"),
            Source_Review_Count=("Requires_Source_Review", "sum"),
        )
        .reset_index()
        .sort_values(
            ["Exception_Count", "Issue_Type"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )


def build_priority_queue(exception_register_df):
    queue = exception_register_df[
        (exception_register_df["Status"] == "REVIEW_REQUIRED")
        & (exception_register_df["Review_Priority"].isin(["P1", "P2"]))
    ].copy()

    return queue.sort_values(
        ["Severity_Rank", "Dataset", "Source_Row_Number", "Column"],
        kind="stable",
    ).reset_index(drop=True)


def validate_exception_register(exception_register_df, rule_catalogue_df):
    checks = []
    required_columns = [
        "Register_ID",
        "Dataset",
        "Record_ID",
        "Column",
        "Issue_Type",
        "Rule_ID",
        "Severity",
        "Status",
        "Recommended_Action",
    ]

    required_values = exception_register_df[required_columns]
    required_missing_count = int(required_values.isna().sum().sum())
    required_blank_count = int(
        (required_values.astype(str).apply(lambda column: column.str.strip()) == "")
        .sum()
        .sum()
    )
    missing_or_blank_count = required_missing_count + required_blank_count

    valid_rule_ids = set(rule_catalogue_df["Rule_ID"].dropna().astype(str))
    allowed_system_rule_ids = {"RECONCILIATION-CHECK"}
    unknown_rule_ids = sorted(
        set(exception_register_df["Rule_ID"].dropna().astype(str))
        - valid_rule_ids
        - allowed_system_rule_ids
    )

    checks.append(
        {
            "Check": "Required register fields are populated",
            "Passed": missing_or_blank_count == 0,
            "Issue_Count": missing_or_blank_count,
            "Details": "OK" if missing_or_blank_count == 0 else "Blank required fields found",
        }
    )
    checks.append(
        {
            "Check": "Register_ID values are unique",
            "Passed": exception_register_df["Register_ID"].is_unique,
            "Issue_Count": int(exception_register_df["Register_ID"].duplicated().sum()),
            "Details": "OK",
        }
    )
    checks.append(
        {
            "Check": "Rule_ID values link back to the rule catalogue or approved system checks",
            "Passed": not unknown_rule_ids,
            "Issue_Count": len(unknown_rule_ids),
            "Details": "; ".join(unknown_rule_ids[:10]) if unknown_rule_ids else "OK",
        }
    )
    checks.append(
        {
            "Check": "All exceptions have a review owner",
            "Passed": (exception_register_df["Review_Owner"].astype(str).str.strip() != "").all(),
            "Issue_Count": int((exception_register_df["Review_Owner"].astype(str).str.strip() == "").sum()),
            "Details": "OK",
        }
    )
    checks.append(
        {
            "Check": "All exceptions have trusted-data guidance",
            "Passed": (exception_register_df["Include_In_Trusted_Data"].astype(str).str.strip() != "").all(),
            "Issue_Count": int((exception_register_df["Include_In_Trusted_Data"].astype(str).str.strip() == "").sum()),
            "Details": "OK",
        }
    )

    return pd.DataFrame(checks)


def run_exception_register(
    exception_candidates=None,
    rule_catalogue=None,
    transformation_issues=None,
    reconciliation_findings=None,
    output_dir=OUTPUT_DIR,
):
    exception_candidates_df = resolve_frame(
        exception_candidates,
        EXCEPTION_CANDIDATES_PATH,
        load_exception_candidates,
    )
    rule_catalogue_df = resolve_frame(
        rule_catalogue,
        RULE_CATALOGUE_PATH,
        load_rule_catalogue,
    )
    transformation_issues_df = resolve_frame(
        transformation_issues,
        TRANSFORMATION_ISSUES_PATH,
        load_transformation_issues,
    )
    reconciliation_findings_df = resolve_frame(
        reconciliation_findings,
        RECONCILIATION_FINDINGS_PATH,
        load_reconciliation_findings,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    exception_register_df = build_exception_register(
        exception_candidates_df,
        rule_catalogue_df,
        transformation_issues_df,
        reconciliation_findings_df,
    )
    register_summary_df = summarise_exception_register(exception_register_df)
    dataset_summary_df = summarise_by_dataset(exception_register_df)
    issue_type_summary_df = summarise_by_issue_type(exception_register_df)
    priority_queue_df = build_priority_queue(exception_register_df)
    validation_summary_df = validate_exception_register(
        exception_register_df,
        rule_catalogue_df,
    )

    exception_register_df.to_csv(output_dir / "exception_register.csv", index=False)
    register_summary_df.to_csv(output_dir / "exception_register_summary.csv", index=False)
    dataset_summary_df.to_csv(output_dir / "exception_register_dataset_summary.csv", index=False)
    issue_type_summary_df.to_csv(output_dir / "exception_register_issue_type_summary.csv", index=False)
    priority_queue_df.to_csv(output_dir / "exception_priority_queue.csv", index=False)
    validation_summary_df.to_csv(output_dir / "exception_register_validation_summary.csv", index=False)

    return {
        "exception_register": exception_register_df,
        "register_summary": register_summary_df,
        "dataset_summary": dataset_summary_df,
        "issue_type_summary": issue_type_summary_df,
        "priority_queue": priority_queue_df,
        "validation_summary": validation_summary_df,
    }
