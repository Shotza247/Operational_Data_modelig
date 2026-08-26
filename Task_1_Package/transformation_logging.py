from pathlib import Path

import pandas as pd


CLEANING_OUTPUT_DIR = Path("standardized_cleaned_data")
RULE_CATALOGUE_PATH = Path("data_inventory/data_quality_rule_catalogue.csv")
TRANSFORMATION_LOG_PATH = CLEANING_OUTPUT_DIR / "transformation_log.csv"
OUTPUT_DIR = CLEANING_OUTPUT_DIR / "transformation_logging"

REQUIRED_LOG_COLUMNS = [
    "Dataset",
    "Source_Row_Index",
    "Source_Row_Number",
    "Record_ID",
    "Column",
    "Original_Value",
    "New_Value",
    "Rule_ID",
    "Rule_Type",
    "Reason",
    "Action_Type",
    "Review_Status",
]

ALLOWED_ACTION_TYPES = {
    "AUTO_CORRECT",
    "EXCLUDE_DUPLICATE_ROW",
}

ALLOWED_REVIEW_STATUSES = {
    "AUTO_ACCEPT",
    "AUTO_CORRECT",
    "REVIEW_REQUIRED",
    "REJECT",
    "UNRESOLVED",
}

AUTO_REVIEW_STATUSES = {
    "AUTO_ACCEPT",
    "AUTO_CORRECT",
}


def load_transformation_log(path=TRANSFORMATION_LOG_PATH):
    return pd.read_csv(path)


def load_rule_catalogue(path=RULE_CATALOGUE_PATH):
    return pd.read_csv(path)


def resolve_frame(value, default_path, loader):
    if isinstance(value, pd.DataFrame):
        return value.copy()

    if value is None:
        return loader(default_path)

    return loader(value)


def count_missing_required_values(transformation_log_df):
    present_columns = [
        column for column in REQUIRED_LOG_COLUMNS if column in transformation_log_df.columns
    ]

    if not present_columns:
        return 0

    missing_mask = transformation_log_df[present_columns].isna()

    for column in present_columns:
        missing_mask[column] = missing_mask[column] | (
            transformation_log_df[column].astype(str).str.strip() == ""
        )

    return int(missing_mask.sum().sum())


def build_validation_summary(transformation_log_df, rule_catalogue_df):
    missing_columns = [
        column
        for column in REQUIRED_LOG_COLUMNS
        if column not in transformation_log_df.columns
    ]

    valid_rule_ids = set(rule_catalogue_df["Rule_ID"].dropna().astype(str))
    observed_rule_ids = set(transformation_log_df.get("Rule_ID", pd.Series(dtype=str)).dropna().astype(str))
    unknown_rule_ids = sorted(observed_rule_ids - valid_rule_ids)
    unknown_rule_ids = [
        rule_id
        for rule_id in unknown_rule_ids
        if rule_id != "CLEANING-NO-CATALOGUE-MATCH"
    ]

    invalid_action_types = sorted(
        set(transformation_log_df.get("Action_Type", pd.Series(dtype=str)).dropna().astype(str))
        - ALLOWED_ACTION_TYPES
    )
    invalid_review_statuses = sorted(
        set(transformation_log_df.get("Review_Status", pd.Series(dtype=str)).dropna().astype(str))
        - ALLOWED_REVIEW_STATUSES
    )

    required_missing_count = count_missing_required_values(transformation_log_df)

    if {"Original_Value", "New_Value"}.issubset(transformation_log_df.columns):
        unchanged_count = int(
            (
                transformation_log_df["Original_Value"].astype(str)
                == transformation_log_df["New_Value"].astype(str)
            ).sum()
        )
    else:
        unchanged_count = 0

    checks = [
        {
            "Check": "Required transformation log columns are present",
            "Passed": not missing_columns,
            "Issue_Count": len(missing_columns),
            "Details": "; ".join(missing_columns) if missing_columns else "OK",
        },
        {
            "Check": "Required evidence fields are populated",
            "Passed": required_missing_count == 0,
            "Issue_Count": required_missing_count,
            "Details": "OK" if required_missing_count == 0 else "Blank evidence cells found",
        },
        {
            "Check": "Rule_ID values link back to the rule catalogue",
            "Passed": not unknown_rule_ids,
            "Issue_Count": len(unknown_rule_ids),
            "Details": "; ".join(unknown_rule_ids[:10]) if unknown_rule_ids else "OK",
        },
        {
            "Check": "Action_Type values are valid",
            "Passed": not invalid_action_types,
            "Issue_Count": len(invalid_action_types),
            "Details": "; ".join(invalid_action_types) if invalid_action_types else "OK",
        },
        {
            "Check": "Review_Status values are valid",
            "Passed": not invalid_review_statuses,
            "Issue_Count": len(invalid_review_statuses),
            "Details": "; ".join(invalid_review_statuses) if invalid_review_statuses else "OK",
        },
        {
            "Check": "Logged changes have different original and new values",
            "Passed": unchanged_count == 0,
            "Issue_Count": unchanged_count,
            "Details": "OK" if unchanged_count == 0 else "Rows logged without a value change",
        },
    ]

    return pd.DataFrame(checks)


def build_validation_issues(transformation_log_df, rule_catalogue_df):
    issue_rows = []

    missing_columns = [
        column
        for column in REQUIRED_LOG_COLUMNS
        if column not in transformation_log_df.columns
    ]
    for column in missing_columns:
        issue_rows.append(
            {
                "Issue_Type": "Missing required column",
                "Severity": "Critical",
                "Dataset": "",
                "Record_ID": "",
                "Column": column,
                "Rule_ID": "",
                "Details": "Transformation log cannot answer audit questions without this column",
            }
        )

    available_columns = [
        column for column in REQUIRED_LOG_COLUMNS if column in transformation_log_df.columns
    ]

    valid_rule_ids = set(rule_catalogue_df["Rule_ID"].dropna().astype(str))

    for row_index, row in transformation_log_df.iterrows():
        for column in available_columns:
            value = row.get(column)
            if pd.isna(value) or str(value).strip() == "":
                issue_rows.append(
                    {
                        "Issue_Type": "Missing required evidence",
                        "Severity": "High",
                        "Dataset": row.get("Dataset", ""),
                        "Record_ID": row.get("Record_ID", ""),
                        "Column": column,
                        "Rule_ID": row.get("Rule_ID", ""),
                        "Details": f"Transformation log row {row_index} has a blank {column}",
                    }
                )

        rule_id = str(row.get("Rule_ID", "")).strip()
        if rule_id and rule_id not in valid_rule_ids and rule_id != "CLEANING-NO-CATALOGUE-MATCH":
            issue_rows.append(
                {
                    "Issue_Type": "Unknown rule id",
                    "Severity": "High",
                    "Dataset": row.get("Dataset", ""),
                    "Record_ID": row.get("Record_ID", ""),
                    "Column": row.get("Column", ""),
                    "Rule_ID": rule_id,
                    "Details": "Rule_ID was not found in the current data quality rule catalogue",
                }
            )

        action_type = str(row.get("Action_Type", "")).strip()
        if action_type and action_type not in ALLOWED_ACTION_TYPES:
            issue_rows.append(
                {
                    "Issue_Type": "Invalid action type",
                    "Severity": "Medium",
                    "Dataset": row.get("Dataset", ""),
                    "Record_ID": row.get("Record_ID", ""),
                    "Column": row.get("Column", ""),
                    "Rule_ID": row.get("Rule_ID", ""),
                    "Details": f"Unexpected Action_Type: {action_type}",
                }
            )

        review_status = str(row.get("Review_Status", "")).strip()
        if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
            issue_rows.append(
                {
                    "Issue_Type": "Invalid review status",
                    "Severity": "Medium",
                    "Dataset": row.get("Dataset", ""),
                    "Record_ID": row.get("Record_ID", ""),
                    "Column": row.get("Column", ""),
                    "Rule_ID": row.get("Rule_ID", ""),
                    "Details": f"Unexpected Review_Status: {review_status}",
                }
            )

        if {"Original_Value", "New_Value"}.issubset(transformation_log_df.columns):
            if str(row.get("Original_Value", "")) == str(row.get("New_Value", "")):
                issue_rows.append(
                    {
                        "Issue_Type": "Unchanged logged value",
                        "Severity": "Low",
                        "Dataset": row.get("Dataset", ""),
                        "Record_ID": row.get("Record_ID", ""),
                        "Column": row.get("Column", ""),
                        "Rule_ID": row.get("Rule_ID", ""),
                        "Details": "Original_Value and New_Value are identical",
                    }
                )

    return pd.DataFrame(
        issue_rows,
        columns=[
            "Issue_Type",
            "Severity",
            "Dataset",
            "Record_ID",
            "Column",
            "Rule_ID",
            "Details",
        ],
    )


def summarise_by_dataset(transformation_log_df):
    grouped = (
        transformation_log_df.groupby("Dataset")
        .agg(
            Transformation_Count=("Dataset", "size"),
            Affected_Record_Count=("Record_ID", "nunique"),
            Affected_Column_Count=("Column", "nunique"),
            Rule_Count=("Rule_ID", "nunique"),
        )
        .reset_index()
    )

    action_counts = (
        transformation_log_df.pivot_table(
            index="Dataset",
            columns="Action_Type",
            values="Record_ID",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    summary = grouped.merge(action_counts, on="Dataset", how="left")

    for column in sorted(ALLOWED_ACTION_TYPES):
        if column not in summary.columns:
            summary[column] = 0

    return summary.sort_values("Transformation_Count", ascending=False).reset_index(drop=True)


def summarise_by_rule(transformation_log_df):
    return (
        transformation_log_df.groupby(
            ["Rule_ID", "Rule_Type", "Reason", "Action_Type", "Review_Status"],
            dropna=False,
        )
        .agg(
            Transformation_Count=("Rule_ID", "size"),
            Dataset_Count=("Dataset", "nunique"),
            Affected_Column_Count=("Column", "nunique"),
        )
        .reset_index()
        .sort_values("Transformation_Count", ascending=False)
        .reset_index(drop=True)
    )


def build_review_queue(transformation_log_df, validation_issues_df):
    needs_review_mask = ~transformation_log_df["Review_Status"].isin(AUTO_REVIEW_STATUSES)
    fallback_rule_mask = transformation_log_df["Rule_ID"] == "CLEANING-NO-CATALOGUE-MATCH"
    queue = transformation_log_df[needs_review_mask | fallback_rule_mask].copy()

    if not validation_issues_df.empty:
        issue_keys = validation_issues_df[["Dataset", "Record_ID", "Column", "Rule_ID"]].drop_duplicates()
        issue_backed_rows = transformation_log_df.merge(
            issue_keys,
            on=["Dataset", "Record_ID", "Column", "Rule_ID"],
            how="inner",
        )
        queue = pd.concat([queue, issue_backed_rows], ignore_index=True)

    if queue.empty:
        return pd.DataFrame(columns=list(transformation_log_df.columns) + ["Review_Reason"])

    queue = queue.drop_duplicates(
        subset=["Dataset", "Source_Row_Number", "Record_ID", "Column", "Rule_ID"]
    )
    queue["Review_Reason"] = queue.apply(describe_review_reason, axis=1)

    return queue.sort_values(["Dataset", "Source_Row_Number", "Column"]).reset_index(drop=True)


def describe_review_reason(row):
    if row.get("Rule_ID") == "CLEANING-NO-CATALOGUE-MATCH":
        return "Cleaning rule did not link to an exact catalogue rule"

    if row.get("Review_Status") not in AUTO_REVIEW_STATUSES:
        return f"Review status is {row.get('Review_Status')}"

    return "Validation issue found in transformation evidence"


def run_transformation_logging(
    transformation_log=None,
    rule_catalogue=None,
    output_dir=OUTPUT_DIR,
):
    transformation_log_df = resolve_frame(
        transformation_log,
        TRANSFORMATION_LOG_PATH,
        load_transformation_log,
    )
    rule_catalogue_df = resolve_frame(
        rule_catalogue,
        RULE_CATALOGUE_PATH,
        load_rule_catalogue,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    validation_summary_df = build_validation_summary(
        transformation_log_df,
        rule_catalogue_df,
    )
    validation_issues_df = build_validation_issues(
        transformation_log_df,
        rule_catalogue_df,
    )
    dataset_summary_df = summarise_by_dataset(transformation_log_df)
    rule_summary_df = summarise_by_rule(transformation_log_df)
    review_queue_df = build_review_queue(transformation_log_df, validation_issues_df)

    validation_summary_df.to_csv(
        output_dir / "transformation_log_validation_summary.csv",
        index=False,
    )
    validation_issues_df.to_csv(
        output_dir / "transformation_log_validation_issues.csv",
        index=False,
    )
    dataset_summary_df.to_csv(
        output_dir / "transformation_log_dataset_summary.csv",
        index=False,
    )
    rule_summary_df.to_csv(
        output_dir / "transformation_log_rule_summary.csv",
        index=False,
    )
    review_queue_df.to_csv(
        output_dir / "transformation_review_queue.csv",
        index=False,
    )

    return {
        "validation_summary": validation_summary_df,
        "validation_issues": validation_issues_df,
        "dataset_summary": dataset_summary_df,
        "rule_summary": rule_summary_df,
        "review_queue": review_queue_df,
    }
