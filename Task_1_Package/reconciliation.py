from pathlib import Path

import pandas as pd


CLEANING_OUTPUT_DIR = Path("standardized_cleaned_data")
OUTPUT_DIR = CLEANING_OUTPUT_DIR / "reconciliation"

OPERATIONAL_DATASETS = [
    "Equipment_Events",
    "Delays_Downtime",
    "Operator_Activities",
    "Shift_Performance",
    "Safety_Observations",
    "Training_Records",
    "Maintenance_Notifications",
    "Environmental_Readings",
    "Access_Control",
]

PRIMARY_KEYS = {
    "Equipment_Events": "Event_ID",
    "Delays_Downtime": "Delay_ID",
    "Operator_Activities": "Activity_ID",
    "Shift_Performance": "Shift_Record_ID",
    "Safety_Observations": "Observation_ID",
    "Training_Records": "Training_Record_ID",
    "Maintenance_Notifications": "Notification_ID",
    "Environmental_Readings": "Reading_ID",
    "Access_Control": "Access_Event_ID",
}

OPERATOR_REFERENCE_DATASETS = [
    "Operator_Activities",
    "Training_Records",
]

OPERATOR_ID_CHECKS = [
    ("Equipment_Events", "Operator_ID"),
    ("Delays_Downtime", "Operator_ID"),
    ("Operator_Activities", "Operator_ID"),
    ("Shift_Performance", "Operator_ID"),
    ("Safety_Observations", "Observed_Person_ID"),
    ("Training_Records", "Operator_ID"),
    ("Access_Control", "Employee_ID"),
]

EQUIPMENT_REFERENCE_COLUMNS = [
    ("Equipment_Events", "Equipment_Name"),
    ("Shift_Performance", "Equipment_Name"),
    ("Maintenance_Notifications", "Equipment_Name"),
]

EQUIPMENT_CHECK_COLUMNS = [
    ("Delays_Downtime", "Equipment_Name"),
    ("Operator_Activities", "Equipment_Name"),
    ("Safety_Observations", "Equipment_Name"),
    ("Environmental_Readings", "Equipment_Nearby"),
]

OPERATOR_PROFILE_COLUMNS = [
    "Operator_Name",
    "Employee_Name",
    "Home_Zone",
    "Contractor_Group",
]

REGISTER_STATUS = "REVIEW_REQUIRED"


def load_cleaned_datasets(output_dir=CLEANING_OUTPUT_DIR):
    output_dir = Path(output_dir)
    datasets = {}

    for dataset in OPERATIONAL_DATASETS:
        path = output_dir / f"{dataset}_cleaned.csv"
        if path.exists():
            datasets[dataset] = pd.read_csv(path)

    return datasets


def parse_datetime_series(values):
    return pd.to_datetime(values, errors="coerce")


def get_record_id(dataset, row):
    key_column = PRIMARY_KEYS.get(dataset)

    if key_column and key_column in row:
        return row.get(key_column, "")

    return ""


def add_finding(
    findings,
    dataset,
    row,
    column,
    issue_type,
    current_value,
    related_dataset="",
    related_record_id="",
    related_column="",
    related_value="",
    related_match_status="MATCH_FOUND",
    check_type="Reconciliation",
    severity="High",
    recommended_action="Review source records and confirm the trusted value",
    evidence="",
):
    findings.append(
        {
            "Dataset": dataset,
            "Source_Row_Index": row.name if hasattr(row, "name") else "",
            "Source_Row_Number": int(row.name) + 2 if hasattr(row, "name") else "",
            "Record_ID": get_record_id(dataset, row),
            "Column": column,
            "Issue_Type": issue_type,
            "Current_Value": current_value,
            "Related_Dataset": related_dataset,
            "Related_Record_ID": related_record_id,
            "Related_Column": related_column,
            "Related_Value": related_value,
            "Related_Match_Status": related_match_status,
            "Check_Type": check_type,
            "Severity": severity,
            "Recommended_Action": recommended_action,
            "Status": REGISTER_STATUS,
            "Evidence": evidence,
        }
    )


def build_operator_reference(datasets):
    operator_ids = set()

    for dataset in OPERATOR_REFERENCE_DATASETS:
        df = datasets.get(dataset)
        if df is None or "Operator_ID" not in df.columns:
            continue

        operator_ids.update(
            df["Operator_ID"].dropna().astype(str).str.strip().loc[lambda values: values != ""]
        )

    return operator_ids


def build_equipment_reference(datasets):
    equipment_ids = set()

    for dataset, column in EQUIPMENT_REFERENCE_COLUMNS:
        df = datasets.get(dataset)
        if df is None or column not in df.columns:
            continue

        equipment_ids.update(
            df[column].dropna().astype(str).str.strip().loc[lambda values: values != ""]
        )

    return equipment_ids


def check_operator_referential_integrity(datasets, findings):
    valid_operator_ids = build_operator_reference(datasets)

    for dataset, column in OPERATOR_ID_CHECKS:
        df = datasets.get(dataset)
        if df is None or column not in df.columns:
            continue

        for _, row in df.iterrows():
            value = row.get(column)
            if pd.isna(value) or str(value).strip() == "":
                continue

            operator_id = str(value).strip()
            if operator_id not in valid_operator_ids:
                add_finding(
                    findings,
                    dataset,
                    row,
                    column,
                    "Operator reference not found",
                    operator_id,
                    related_dataset="Operator_Activities; Training_Records",
                    related_record_id="NO_MATCH_FOUND",
                    related_column="Operator_ID",
                    related_match_status="NO_MATCH",
                    check_type="Referential integrity",
                    severity="Critical",
                    recommended_action="Confirm whether the operator exists or correct the operator identifier",
                    evidence=f"{operator_id} is absent from operator reference datasets",
                )


def check_equipment_referential_integrity(datasets, findings):
    valid_equipment_ids = build_equipment_reference(datasets)

    for dataset, column in EQUIPMENT_CHECK_COLUMNS:
        df = datasets.get(dataset)
        if df is None or column not in df.columns:
            continue

        for _, row in df.iterrows():
            value = row.get(column)
            if pd.isna(value) or str(value).strip() == "":
                continue

            equipment_id = str(value).strip()
            if equipment_id not in valid_equipment_ids:
                add_finding(
                    findings,
                    dataset,
                    row,
                    column,
                    "Equipment reference not found",
                    equipment_id,
                    related_dataset="Equipment_Events; Shift_Performance; Maintenance_Notifications",
                    related_record_id="NO_MATCH_FOUND",
                    related_column="Equipment_Name",
                    related_match_status="NO_MATCH",
                    check_type="Referential integrity",
                    severity="High",
                    recommended_action="Confirm whether the equipment exists or correct the equipment identifier",
                    evidence=f"{equipment_id} is absent from equipment reference datasets",
                )


def collect_operator_profiles(datasets):
    frames = []

    for dataset_name, df in datasets.items():
        id_column = "Operator_ID"
        if dataset_name == "Access_Control":
            id_column = "Employee_ID"

        if id_column not in df.columns:
            continue

        available_columns = [
            column
            for column in OPERATOR_PROFILE_COLUMNS
            if column in df.columns
        ]

        if not available_columns:
            continue

        profile = df[[id_column] + available_columns].copy()
        profile = profile.rename(columns={id_column: "Operator_ID"})
        profile["Source_Dataset"] = dataset_name
        frames.append(profile)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True, sort=False)


def check_operator_profile_consistency(datasets, findings):
    profiles = collect_operator_profiles(datasets)

    if profiles.empty:
        return

    profile_columns = [
        column
        for column in OPERATOR_PROFILE_COLUMNS
        if column in profiles.columns
    ]

    for operator_id, group in profiles.groupby("Operator_ID"):
        if pd.isna(operator_id) or str(operator_id).strip() == "":
            continue

        for column in profile_columns:
            values = (
                group[column]
                .dropna()
                .astype(str)
                .str.strip()
                .loc[lambda series: series != ""]
                .unique()
            )
            if len(values) <= 1:
                continue

            for _, profile_row in group[group[column].astype(str).str.strip().isin(values)].iterrows():
                source_dataset = profile_row["Source_Dataset"]
                source_df = datasets[source_dataset]
                source_match = source_df[
                    source_df.get("Operator_ID", source_df.get("Employee_ID")).astype(str)
                    == str(operator_id)
                ]
                source_row = (
                    source_match.iloc[0]
                    if not source_match.empty
                    else pd.Series(dtype=object)
                )
                source_row.name = (
                    source_match.index[0]
                    if not source_match.empty
                    else profile_row.name
                )
                add_finding(
                    findings,
                    source_dataset,
                    source_row,
                    column,
                    "Operator profile conflict",
                    profile_row.get(column, ""),
                    related_dataset="; ".join(sorted(group["Source_Dataset"].unique())),
                    related_record_id=str(operator_id),
                    related_column=column,
                    related_value=" | ".join(sorted(values)),
                    check_type="Cross-dataset consistency",
                    severity="High",
                    recommended_action="Review operator master data and align the trusted profile attributes",
                    evidence=f"{operator_id} has conflicting {column} values: {' | '.join(sorted(values))}",
                )


def get_interval(row, start_column, end_column):
    start = pd.to_datetime(row.get(start_column), errors="coerce")
    end = pd.to_datetime(row.get(end_column), errors="coerce")

    if pd.isna(start) or pd.isna(end):
        return None

    return start, end


def intervals_overlap(left_start, left_end, right_start, right_end):
    return left_start <= right_end and right_start <= left_end


def check_activity_delay_conflicts(datasets, findings):
    activities = datasets.get("Operator_Activities")
    delays = datasets.get("Delays_Downtime")

    if activities is None or delays is None:
        return

    for _, activity in activities.iterrows():
        activity_interval = get_interval(activity, "Activity_Start", "Activity_End")
        if activity_interval is None:
            continue

        activity_start, activity_end = activity_interval
        equipment = str(activity.get("Equipment_Name", "")).strip()
        if not equipment:
            continue

        related_delays = delays[
            delays["Equipment_Name"].astype(str).str.strip() == equipment
        ]

        for _, delay in related_delays.iterrows():
            delay_interval = get_interval(delay, "Start_Time", "End_Time")
            if delay_interval is None:
                continue

            delay_start, delay_end = delay_interval
            if intervals_overlap(activity_start, activity_end, delay_start, delay_end):
                add_finding(
                    findings,
                    "Operator_Activities",
                    activity,
                    "Activity_Start|Activity_End",
                    "Activity overlaps recorded downtime",
                    f"{activity_start} -> {activity_end}",
                    related_dataset="Delays_Downtime",
                    related_record_id=delay.get("Delay_ID", ""),
                    related_column="Start_Time|End_Time",
                    related_value=f"{delay_start} -> {delay_end}",
                    check_type="Equipment/event conflict",
                    severity="High",
                    recommended_action="Confirm whether the activity or downtime interval is correct",
                    evidence=f"{equipment} activity overlaps downtime record {delay.get('Delay_ID', '')}",
                )


def check_activity_maintenance_conflicts(datasets, findings):
    activities = datasets.get("Operator_Activities")
    maintenance = datasets.get("Maintenance_Notifications")

    if activities is None or maintenance is None:
        return

    for _, activity in activities.iterrows():
        activity_interval = get_interval(activity, "Activity_Start", "Activity_End")
        if activity_interval is None:
            continue

        activity_start, activity_end = activity_interval
        equipment = str(activity.get("Equipment_Name", "")).strip()
        if not equipment:
            continue

        related_maintenance = maintenance[
            maintenance["Equipment_Name"].astype(str).str.strip() == equipment
        ]

        for _, work_order in related_maintenance.iterrows():
            maintenance_interval = get_interval(work_order, "Actual_Start", "Actual_End")
            if maintenance_interval is None:
                continue

            maintenance_start, maintenance_end = maintenance_interval
            if intervals_overlap(
                activity_start,
                activity_end,
                maintenance_start,
                maintenance_end,
            ):
                add_finding(
                    findings,
                    "Operator_Activities",
                    activity,
                    "Activity_Start|Activity_End",
                    "Activity overlaps recorded maintenance",
                    f"{activity_start} -> {activity_end}",
                    related_dataset="Maintenance_Notifications",
                    related_record_id=work_order.get("Notification_ID", ""),
                    related_column="Actual_Start|Actual_End",
                    related_value=f"{maintenance_start} -> {maintenance_end}",
                    check_type="Equipment/event conflict",
                    severity="Critical",
                    recommended_action="Confirm whether the equipment was available for operation during maintenance",
                    evidence=f"{equipment} activity overlaps maintenance record {work_order.get('Notification_ID', '')}",
                )


def check_access_activity_conflicts(datasets, findings):
    access = datasets.get("Access_Control")
    activities = datasets.get("Operator_Activities")

    if access is None or activities is None:
        return

    denied_access = access[
        access["Access_Result"].astype(str).str.lower().str.strip() == "denied"
    ].copy()
    denied_access["Parsed_Event_Time"] = parse_datetime_series(denied_access["Event_Time"])

    for _, access_row in denied_access.iterrows():
        event_time = access_row.get("Parsed_Event_Time")
        employee_id = str(access_row.get("Employee_ID", "")).strip()

        if pd.isna(event_time) or not employee_id:
            continue

        employee_activities = activities[
            activities["Operator_ID"].astype(str).str.strip() == employee_id
        ]

        for _, activity in employee_activities.iterrows():
            activity_interval = get_interval(activity, "Activity_Start", "Activity_End")
            if activity_interval is None:
                continue

            activity_start, activity_end = activity_interval
            if activity_start <= event_time <= activity_end:
                add_finding(
                    findings,
                    "Access_Control",
                    access_row,
                    "Access_Result",
                    "Denied access during recorded activity",
                    access_row.get("Access_Result", ""),
                    related_dataset="Operator_Activities",
                    related_record_id=activity.get("Activity_ID", ""),
                    related_column="Activity_Start|Activity_End",
                    related_value=f"{activity_start} -> {activity_end}",
                    check_type="Operator/activity conflict",
                    severity="High",
                    recommended_action="Confirm whether the access denial or activity record is correct",
                    evidence=f"{employee_id} has denied access during activity {activity.get('Activity_ID', '')}",
                )


def run_reconciliation_checks(cleaned_datasets):
    findings = []

    check_operator_referential_integrity(cleaned_datasets, findings)
    check_equipment_referential_integrity(cleaned_datasets, findings)
    check_operator_profile_consistency(cleaned_datasets, findings)
    check_activity_delay_conflicts(cleaned_datasets, findings)
    check_activity_maintenance_conflicts(cleaned_datasets, findings)
    check_access_activity_conflicts(cleaned_datasets, findings)

    findings_df = pd.DataFrame(findings)

    if findings_df.empty:
        findings_df = pd.DataFrame(
            columns=[
                "Dataset",
                "Source_Row_Index",
                "Source_Row_Number",
                "Record_ID",
                "Column",
                "Issue_Type",
                "Current_Value",
                "Related_Dataset",
                "Related_Record_ID",
                "Related_Column",
                "Related_Value",
                "Related_Match_Status",
                "Check_Type",
                "Severity",
                "Recommended_Action",
                "Status",
                "Evidence",
            ]
        )

    findings_df = findings_df.reset_index(drop=True)
    findings_df.insert(
        0,
        "Reconciliation_ID",
        [f"REC-{row_number:05d}" for row_number in range(1, len(findings_df) + 1)],
    )

    return findings_df


def summarise_reconciliation(findings_df):
    if findings_df.empty:
        return pd.DataFrame(
            [
                {"Metric": "Total reconciliation findings", "Value": 0},
                {"Metric": "Critical findings", "Value": 0},
                {"Metric": "High findings", "Value": 0},
            ]
        )

    return pd.DataFrame(
        [
            {
                "Metric": "Total reconciliation findings",
                "Value": len(findings_df),
            },
            {
                "Metric": "Critical findings",
                "Value": int((findings_df["Severity"] == "Critical").sum()),
            },
            {
                "Metric": "High findings",
                "Value": int((findings_df["Severity"] == "High").sum()),
            },
            {
                "Metric": "Datasets with findings",
                "Value": findings_df["Dataset"].nunique(),
            },
            {
                "Metric": "Affected records",
                "Value": findings_df["Record_ID"].nunique(),
            },
        ]
    )


def summarise_by_dataset(findings_df):
    if findings_df.empty:
        return pd.DataFrame(
            columns=[
                "Dataset",
                "Finding_Count",
                "Critical_Count",
                "High_Count",
                "Affected_Record_Count",
                "Check_Type_Count",
            ]
        )

    return (
        findings_df.groupby("Dataset")
        .agg(
            Finding_Count=("Reconciliation_ID", "count"),
            Critical_Count=("Severity", lambda values: int((values == "Critical").sum())),
            High_Count=("Severity", lambda values: int((values == "High").sum())),
            Affected_Record_Count=("Record_ID", "nunique"),
            Check_Type_Count=("Check_Type", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["Critical_Count", "High_Count", "Finding_Count"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )


def summarise_by_check(findings_df):
    if findings_df.empty:
        return pd.DataFrame(
            columns=[
                "Check_Type",
                "Issue_Type",
                "Severity",
                "Finding_Count",
                "Dataset_Count",
            ]
        )

    return (
        findings_df.groupby(["Check_Type", "Issue_Type", "Severity"])
        .agg(
            Finding_Count=("Reconciliation_ID", "count"),
            Dataset_Count=("Dataset", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["Finding_Count", "Check_Type", "Issue_Type"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def validate_reconciliation(findings_df):
    required_columns = [
        "Reconciliation_ID",
        "Dataset",
        "Record_ID",
        "Column",
        "Issue_Type",
        "Related_Dataset",
        "Related_Record_ID",
        "Related_Column",
        "Related_Match_Status",
        "Check_Type",
        "Severity",
        "Recommended_Action",
        "Status",
        "Evidence",
    ]

    required_values = findings_df[required_columns]
    missing_or_blank_count = int(required_values.isna().sum().sum())
    missing_or_blank_count += int(
        (required_values.astype(str).apply(lambda column: column.str.strip()) == "")
        .sum()
        .sum()
    )
    duplicated_id_count = int(findings_df["Reconciliation_ID"].duplicated().sum())

    checks = [
        {
            "Check": "Required reconciliation fields are populated",
            "Passed": missing_or_blank_count == 0,
            "Issue_Count": missing_or_blank_count,
            "Details": "OK" if missing_or_blank_count == 0 else "Blank required fields found",
        },
        {
            "Check": "Reconciliation_ID values are unique",
            "Passed": duplicated_id_count == 0,
            "Issue_Count": duplicated_id_count,
            "Details": "OK" if duplicated_id_count == 0 else "Duplicate IDs found",
        },
        {
            "Check": "Findings are marked for review",
            "Passed": (findings_df["Status"] == REGISTER_STATUS).all(),
            "Issue_Count": int((findings_df["Status"] != REGISTER_STATUS).sum()),
            "Details": "OK",
        },
    ]

    return pd.DataFrame(checks)


def run_reconciliation(cleaned_datasets=None, output_dir=OUTPUT_DIR):
    if cleaned_datasets is None:
        cleaned_datasets = load_cleaned_datasets()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    findings_df = run_reconciliation_checks(cleaned_datasets)
    summary_df = summarise_reconciliation(findings_df)
    dataset_summary_df = summarise_by_dataset(findings_df)
    check_summary_df = summarise_by_check(findings_df)
    validation_summary_df = validate_reconciliation(findings_df)

    findings_df.to_csv(output_dir / "reconciliation_findings.csv", index=False)
    summary_df.to_csv(output_dir / "reconciliation_summary.csv", index=False)
    dataset_summary_df.to_csv(output_dir / "reconciliation_dataset_summary.csv", index=False)
    check_summary_df.to_csv(output_dir / "reconciliation_check_summary.csv", index=False)
    validation_summary_df.to_csv(output_dir / "reconciliation_validation_summary.csv", index=False)

    return {
        "findings": findings_df,
        "summary": summary_df,
        "dataset_summary": dataset_summary_df,
        "check_summary": check_summary_df,
        "validation_summary": validation_summary_df,
    }
