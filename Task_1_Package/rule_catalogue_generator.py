from pathlib import Path

import pandas as pd

BASE_COLUMNS = [
    "Rule_ID",
    "Dataset",
    "Column",
    "Rule_Type",
    "Valid_Condition",
    "Action",
    "Auto_Correct_Allowed",
    "Severity",
    "Reason",
]

AUDIT_COLUMNS = [
    "Rule_Source",
    "Evidence",
]

CATALOGUE_COLUMNS = BASE_COLUMNS + AUDIT_COLUMNS

DOMAIN_OVERRIDE_COLUMNS = [
    "Dataset",
    "Column",
    "Rule_Type",
    "Valid_Condition",
    "Action",
    "Auto_Correct_Allowed",
    "Severity",
    "Reason",
    "Rule_Source",
    "Evidence",
]

DATE_KEYWORDS = [
    "date",
    "time",
    "start",
    "end",
    "expiry",
    "completion",
    "calibration",
    "raised",
    "closed",
    "planned",
    "actual",
]

ID_PATTERNS = {
    "Access_Event_ID": "ACC followed by four digits",
    "Activity_ID": "ACT followed by four digits",
    "Badge_ID": "BDG dash four digits",
    "Delay_ID": "DLY followed by four digits",
    "Device_ID": "DEV dash digits",
    "Employee_ID": "OP followed by four digits unless explicitly external",
    "Event_ID": "EVT followed by four digits",
    "Notification_ID": "MNT followed by four digits",
    "Observation_ID": "SAF followed by four digits",
    "Operator_ID": "OP followed by four digits",
    "Reading_ID": "ENV followed by four digits",
    "Reporter_ID": "OP or SUP followed by digits",
    "Sensor_ID": "SNS dash two digits",
    "Shift_Record_ID": "SHF followed by four digits",
    "Supervisor_ID": "SUP followed by two digits",
    "Training_Record_ID": "TRN followed by four digits",
    "Work_Order_ID": "WO dash five digits",
}

def clean_csv_frame(df):
    unnamed_columns = [
        column for column in df.columns
        if str(column).startswith("Unnamed")
    ]
    return df.drop(columns=unnamed_columns, errors="ignore")


def load_inventory_inputs(data_inventory_dir="data_inventory"):
    data_inventory_dir = Path(data_inventory_dir)

    inputs = {
        "data_inventory_dir": data_inventory_dir,
        "column_profile": clean_csv_frame(
            pd.read_csv(data_inventory_dir / "datasheet-column-level.csv")
        ),
        "missing_profile": clean_csv_frame(
            pd.read_csv(data_inventory_dir / "missing-value_profile.csv")
        ),
        "highlevel_inventory": clean_csv_frame(
            pd.read_csv(data_inventory_dir / "datasheet_Highlevel_inventory.csv")
        ),
        "privacy_inventory": clean_csv_frame(
            pd.read_csv(data_inventory_dir / "privacy_sensitive_fields.csv")
        ),
        "data_dictionary": clean_csv_frame(
            pd.read_csv(data_inventory_dir / "data_dictionary.csv")
        ),
        "numeric_profiles": load_numeric_profiles(data_inventory_dir),
        "domain_overrides": load_domain_overrides(data_inventory_dir),
    }

    return inputs


def load_numeric_profiles(data_inventory_dir):
    numeric_profiles = {}

    for path in sorted(Path(data_inventory_dir).glob("*_numeric_profile.csv")):
        dataset = path.name.replace("_numeric_profile.csv", "")
        profile_df = pd.read_csv(path)

        first_column = profile_df.columns[0]
        if str(first_column).startswith("Unnamed"):
            profile_df = profile_df.rename(columns={first_column: "Column"})

        numeric_profiles[dataset] = profile_df

    return numeric_profiles


def load_domain_overrides(data_inventory_dir):
    override_path = Path(data_inventory_dir) / "rule_domain_overrides.csv"

    if not override_path.exists():
        pd.DataFrame(columns=DOMAIN_OVERRIDE_COLUMNS).to_csv(
            override_path,
            index=False,
        )

    return pd.read_csv(override_path)


def add_rule(
    rules,
    dataset,
    column,
    rule_type,
    valid_condition,
    action,
    auto_correct_allowed,
    severity,
    reason,
    rule_source,
    evidence,
):
    rules.append(
        {
            "Dataset": dataset,
            "Column": column,
            "Rule_Type": rule_type,
            "Valid_Condition": valid_condition,
            "Action": action,
            "Auto_Correct_Allowed": bool(auto_correct_allowed),
            "Severity": severity,
            "Reason": reason,
            "Rule_Source": rule_source,
            "Evidence": evidence,
        }
    )


def is_datetime_column(column):
    column_lower = str(column).lower()
    return any(keyword in column_lower for keyword in DATE_KEYWORDS)


def is_unit_column(column):
    return "unit" in str(column).lower()


def is_percent_column(column):
    return "pct" in str(column).lower() or "%" in str(column)


def is_id_column(column):
    return str(column).endswith("_ID")


def is_probable_primary_key(row):
    column = str(row["Column"])
    row_count = int(row["Row_Count"])
    unique_count = int(row["Unique_Count"])
    duplicate_value_count = int(row["Duplicate_Value_Count"])

    return (
        is_id_column(column)
        and unique_count >= row_count - 1
        and duplicate_value_count <= 2
    )


def missing_severity(column, missing_pct):
    if is_id_column(column):
        return "High"
    if missing_pct >= 50:
        return "High"
    if missing_pct >= 20:
        return "Medium"
    return "Low"


def infer_exact_duplicate_rules(highlevel_inventory):
    rules = []

    for _, row in highlevel_inventory.iterrows():
        duplicate_rows = int(row["Duplicate_Rows_Detected"])

        if duplicate_rows > 0:
            add_rule(
                rules,
                row["Dataset"],
                "Entire row",
                "Uniqueness",
                "Exact duplicate rows should not appear in the trusted layer",
                "Flag duplicate rows and exclude later duplicates only after logging",
                False,
                "High",
                "Exact duplicate rows can inflate operational counts",
                "Generated from datasheet_Highlevel_inventory.csv",
                f"Duplicate_Rows_Detected={duplicate_rows}",
            )

    return rules


def infer_identifier_rules(column_profile):
    rules = []

    for _, row in column_profile.iterrows():
        dataset = row["Dataset"]
        column = row["Column"]

        if not is_id_column(column):
            continue

        pattern = ID_PATTERNS.get(column, "a documented identifier pattern")

        add_rule(
            rules,
            dataset,
            column,
            "Validity",
            f"Identifier should match {pattern}",
            "Flag missing or malformed identifier values",
            False,
            "High",
            "Identifier format supports row-level audit and joins",
            "Generated from datasheet-column-level.csv",
            f"Column ends with _ID; Unique_Count={row['Unique_Count']}",
        )

        if is_probable_primary_key(row):
            add_rule(
                rules,
                dataset,
                column,
                "Uniqueness",
                "Identifier should be unique at the dataset grain",
                "Flag duplicate identifiers and retain raw rows for review",
                False,
                "Critical",
                "Primary identifier duplication breaks trusted row grain",
                "Generated from datasheet-column-level.csv",
                (
                    f"Row_Count={row['Row_Count']}; "
                    f"Unique_Count={row['Unique_Count']}; "
                    f"Duplicate_Value_Count={row['Duplicate_Value_Count']}"
                ),
            )

            add_rule(
                rules,
                dataset,
                column,
                "Completeness",
                "Primary identifier must be populated",
                "Flag missing primary identifiers as exceptions",
                False,
                "Critical",
                "Blank primary identifiers break traceability",
                "Generated from datasheet-column-level.csv",
                f"Missing_Count={row['Missing_Count']}",
            )

    return rules


def infer_missingness_rules(missing_profile):
    rules = []

    for _, row in missing_profile.iterrows():
        missing_count = int(row["Missing_Count"])
        missing_pct = float(row["Missing_Pct(%)"])

        if missing_count == 0:
            continue

        dataset = row["Dataset"]
        column = row["Column"]

        add_rule(
            rules,
            dataset,
            column,
            "Completeness",
            "Missing values must be explained by a valid business reason",
            "Flag missing values for review before trusted use",
            False,
            missing_severity(column, missing_pct),
            "Profiling detected missing values in this column",
            "Generated from missing-value_profile.csv",
            f"Missing_Count={missing_count}; Missing_Pct={missing_pct}",
        )

    return rules


def infer_datetime_rules(column_profile):
    rules = []

    for _, row in column_profile.iterrows():
        column = row["Column"]

        if not is_datetime_column(column):
            continue

        add_rule(
            rules,
            row["Dataset"],
            column,
            "Validity",
            "Date/time values should parse to a single ISO date or datetime standard",
            "Standardise parseable values and flag ambiguous or unparseable values",
            True,
            "High",
            "Profile shows date/time-like field requiring consistent parsing",
            "Generated from datasheet-column-level.csv",
            f"Sample_Values={row['Sample_Values']}",
        )

    return rules


def infer_temporal_pair_rules(column_profile):
    rules = []

    temporal_pairs = [
        ("Delays_Downtime", "Start_Time", "End_Time", "End_Time must be after Start_Time"),
        ("Operator_Activities", "Activity_Start", "Activity_End", "Activity_End must be after Activity_Start"),
        ("Safety_Observations", "Observation_Date", "Closed_Date", "Closed_Date must not be before Observation_Date when populated"),
        ("Training_Records", "Completion_Date", "Expiry_Date", "Expiry_Date must be after Completion_Date"),
        ("Maintenance_Notifications", "Actual_Start", "Actual_End", "Actual_End must be after Actual_Start when both are populated"),
        ("Environmental_Readings", "Reading_Time", "Calibration_Due", "Calibration_Due should not be before Reading_Time"),
    ]

    available_columns = {
        (row["Dataset"], row["Column"])
        for _, row in column_profile.iterrows()
    }

    for dataset, start_column, end_column, condition in temporal_pairs:
        if (
            (dataset, start_column) not in available_columns
            or (dataset, end_column) not in available_columns
        ):
            continue

        add_rule(
            rules,
            dataset,
            f"{start_column}|{end_column}",
            "Temporal integrity",
            condition,
            "Flag temporal contradictions for review",
            False,
            "Critical",
            "Timestamp ordering affects duration, validity, or workflow status",
            "Generated from recognised timestamp column pairs",
            f"Detected columns: {start_column}, {end_column}",
        )

    return rules


def infer_numeric_rules(numeric_profiles):
    rules = []

    for dataset, profile_df in numeric_profiles.items():
        for _, row in profile_df.iterrows():
            column = row["Column"]
            minimum = float(row["min"])
            maximum = float(row["max"])
            upper_quartile = float(row["75%"])

            if minimum < 0:
                add_rule(
                    rules,
                    dataset,
                    column,
                    "Plausibility",
                    "Numeric value should not be negative unless the data dictionary permits it",
                    "Flag negative values for review",
                    False,
                    "High",
                    "Numeric profile detected values below zero",
                    f"Generated from {dataset}_numeric_profile.csv",
                    f"min={minimum}",
                )

            if is_percent_column(column):
                add_rule(
                    rules,
                    dataset,
                    column,
                    "Plausibility",
                    "Percentage fields should be within the documented percentage scale",
                    "Flag values outside the expected range before analysis",
                    False,
                    "High",
                    "Percentage metrics must be bounded before performance reporting",
                    f"Generated from {dataset}_numeric_profile.csv",
                    f"min={minimum}; max={maximum}",
                )

            if str(column).lower() == "score":
                add_rule(
                    rules,
                    dataset,
                    column,
                    "Plausibility",
                    "Scores should be between 0 and 100",
                    "Flag scores outside 0 to 100",
                    False,
                    "High",
                    "Training score profile indicates values may exceed expected score range",
                    f"Generated from {dataset}_numeric_profile.csv",
                    f"min={minimum}; max={maximum}",
                )

            if "hours" in str(column).lower():
                add_rule(
                    rules,
                    dataset,
                    column,
                    "Plausibility",
                    "Hour values should be non-negative and plausible for the operating window",
                    "Flag impossible or extreme hour values",
                    False,
                    "High" if maximum > 24 or minimum < 0 else "Medium",
                    "Hour-based measures directly affect availability and downtime analysis",
                    f"Generated from {dataset}_numeric_profile.csv",
                    f"min={minimum}; max={maximum}",
                )

            if upper_quartile > 0 and maximum > upper_quartile * 10:
                add_rule(
                    rules,
                    dataset,
                    column,
                    "Plausibility",
                    "Extreme numeric outliers should be reviewed before trusted use",
                    "Flag statistical outliers for review",
                    False,
                    "High",
                    "Profile max is more than ten times the upper quartile",
                    f"Generated from {dataset}_numeric_profile.csv",
                    f"75%={upper_quartile}; max={maximum}",
                )

    return rules


def infer_unit_rules(column_profile):
    rules = []

    for _, row in column_profile.iterrows():
        column = row["Column"]

        if not is_unit_column(column):
            continue

        add_rule(
            rules,
            row["Dataset"],
            column,
            "Consistency",
            "Unit values must be canonical before numeric comparison",
            "Standardise supported units and log each conversion",
            True,
            "High",
            "Unit columns control whether numeric values are comparable",
            "Generated from datasheet-column-level.csv",
            f"Unique_Count={row['Unique_Count']}; Sample_Values={row['Sample_Values']}",
        )

    return rules


def infer_categorical_rules(column_profile):
    rules = []

    excluded_columns = {"Comment", "Description", "Supervisor_Comment"}

    for _, row in column_profile.iterrows():
        column = row["Column"]
        data_type = str(row["Data_Type"]).lower()
        unique_count = int(row["Unique_Count"])

        if column in excluded_columns:
            continue
        if is_datetime_column(column) or is_id_column(column) or is_unit_column(column):
            continue
        if data_type not in {"object", "str", "string"}:
            continue
        if unique_count > 10:
            continue

        add_rule(
            rules,
            row["Dataset"],
            column,
            "Validity",
            "Low-cardinality categorical values should use a controlled vocabulary",
            "Standardise known casing or spelling variants and flag unknown categories",
            True,
            "Medium",
            "Profile shows a small set of repeated categorical values",
            "Generated from datasheet-column-level.csv",
            f"Unique_Count={unique_count}; Sample_Values={row['Sample_Values']}",
        )

    return rules


def infer_privacy_rules(privacy_inventory):
    rules = []

    for _, row in privacy_inventory.iterrows():
        add_rule(
            rules,
            row["Dataset"],
            row["Column"],
            "Privacy",
            "Potentially sensitive fields should be purpose-limited before analytical use",
            "Flag field for privacy-aware handling in cleaned and trusted layers",
            False,
            "High",
            "Privacy inventory detected identity, proxy, or sensitive attribute",
            "Generated from privacy_sensitive_fields.csv",
            "Potential_Sensitivity=True",
        )

    return rules


def infer_dictionary_guidance_rules(data_dictionary):
    rules = []

    for _, row in data_dictionary.iterrows():
        add_rule(
            rules,
            row["Dataset"],
            row["Field"],
            "Data dictionary guidance",
            row["Expected / canonical guidance"],
            "Use this guidance to decide whether to auto-correct, flag, exclude, or reconcile",
            False,
            dictionary_severity(row["Sensitivity"]),
            row["Plain-language description"],
            "Generated from data_dictionary.csv",
            f"Sensitivity={row['Sensitivity']}",
        )

    return rules


def dictionary_severity(sensitivity):
    sensitivity = str(sensitivity).lower()

    if "sensitive personal" in sensitivity:
        return "Critical"
    if "personal" in sensitivity or "sensitive" in sensitivity:
        return "High"
    return "Medium"


def append_domain_overrides(rules, domain_overrides):
    if domain_overrides.empty:
        return rules

    for _, row in domain_overrides.iterrows():
        add_rule(
            rules,
            row["Dataset"],
            row["Column"],
            row["Rule_Type"],
            row["Valid_Condition"],
            row["Action"],
            str(row["Auto_Correct_Allowed"]).upper() == "TRUE",
            row["Severity"],
            row["Reason"],
            row.get("Rule_Source", "Human domain override"),
            row.get("Evidence", "rule_domain_overrides.csv"),
        )

    return rules


def finalise_rule_catalogue(rules):
    rule_catalogue_df = pd.DataFrame(rules)

    if rule_catalogue_df.empty:
        return pd.DataFrame(columns=CATALOGUE_COLUMNS)

    dedupe_columns = [
        "Dataset",
        "Column",
        "Rule_Type",
        "Valid_Condition",
        "Action",
    ]

    rule_catalogue_df = (
        rule_catalogue_df
        .drop_duplicates(subset=dedupe_columns)
        .sort_values(["Dataset", "Column", "Rule_Type", "Severity"])
        .reset_index(drop=True)
    )

    rule_catalogue_df.insert(
        0,
        "Rule_ID",
        [f"DQ-{index:04d}" for index in range(1, len(rule_catalogue_df) + 1)],
    )

    return rule_catalogue_df[CATALOGUE_COLUMNS]


def build_rule_catalogue(inputs):
    rules = []

    rules.extend(infer_exact_duplicate_rules(inputs["highlevel_inventory"]))
    rules.extend(infer_identifier_rules(inputs["column_profile"]))
    rules.extend(infer_missingness_rules(inputs["missing_profile"]))
    rules.extend(infer_datetime_rules(inputs["column_profile"]))
    rules.extend(infer_temporal_pair_rules(inputs["column_profile"]))
    rules.extend(infer_numeric_rules(inputs["numeric_profiles"]))
    rules.extend(infer_unit_rules(inputs["column_profile"]))
    rules.extend(infer_categorical_rules(inputs["column_profile"]))
    rules.extend(infer_privacy_rules(inputs["privacy_inventory"]))
    rules.extend(infer_dictionary_guidance_rules(inputs["data_dictionary"]))
    rules = append_domain_overrides(rules, inputs["domain_overrides"])

    return finalise_rule_catalogue(rules)


def validate_rule_catalogue(rule_catalogue_df):
    missing_columns = [
        column for column in CATALOGUE_COLUMNS
        if column not in rule_catalogue_df.columns
    ]

    duplicate_rule_ids = int(rule_catalogue_df["Rule_ID"].duplicated().sum())

    blank_required_fields = int(
        rule_catalogue_df[BASE_COLUMNS]
        .isna()
        .sum()
        .sum()
    )

    invalid_auto_correct_values = sorted(
        set(rule_catalogue_df["Auto_Correct_Allowed"].astype(str).str.upper())
        - {"TRUE", "FALSE"}
    )

    invalid_severities = sorted(
        set(rule_catalogue_df["Severity"])
        - {"Low", "Medium", "High", "Critical"}
    )

    return pd.DataFrame(
        [
            {
                "Check": "Expected columns present",
                "Passed": len(missing_columns) == 0,
                "Details": "; ".join(missing_columns) if missing_columns else "OK",
            },
            {
                "Check": "Rule_ID values are unique",
                "Passed": duplicate_rule_ids == 0,
                "Details": duplicate_rule_ids,
            },
            {
                "Check": "Required fields are populated",
                "Passed": blank_required_fields == 0,
                "Details": blank_required_fields,
            },
            {
                "Check": "Auto_Correct_Allowed is boolean",
                "Passed": len(invalid_auto_correct_values) == 0,
                "Details": "; ".join(invalid_auto_correct_values) if invalid_auto_correct_values else "OK",
            },
            {
                "Check": "Severity values are valid",
                "Passed": len(invalid_severities) == 0,
                "Details": "; ".join(invalid_severities) if invalid_severities else "OK",
            },
        ]
    )


def summarise_rule_catalogue(rule_catalogue_df):
    return {
        "rules_by_type": rule_catalogue_df["Rule_Type"].value_counts().sort_index(),
        "rules_by_severity": rule_catalogue_df["Severity"].value_counts().reindex(
            ["Critical", "High", "Medium", "Low"],
            fill_value=0,
        ),
        "rules_by_source": rule_catalogue_df["Rule_Source"].value_counts().sort_index(),
        "auto_correct_allowed": rule_catalogue_df["Auto_Correct_Allowed"].value_counts(),
    }


def save_rule_catalogue(
    rule_catalogue_df,
    output_path="data_inventory/data_quality_rule_catalogue.csv",
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rule_catalogue_df.to_csv(output_path, index=False)
    return output_path
