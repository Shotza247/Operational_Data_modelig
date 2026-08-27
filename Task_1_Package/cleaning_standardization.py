from pathlib import Path
import re

import pandas as pd


OUTPUT_DIR = Path("standardized_cleaned_data")
RULE_CATALOGUE_PATH = Path("data_inventory/data_quality_rule_catalogue.csv")

OPERATIONAL_SHEETS = [
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

EQUIPMENT_REFERENCE_COLUMNS = [
    "Equipment_Name",
    "Equipment_Nearby",
]

WORD_NUMBERS = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    "SIX": 6,
    "SEVEN": 7,
    "EIGHT": 8,
    "NINE": 9,
    "TEN": 10,
}

CATEGORY_MAPPINGS = {
    "Event_Type": {
        "start": "Start",
        "strat": "Start",
        "stop": "Stop",
        "idle": "Idle",
        "inspection": "Inspection",
        "fault": "Fault",
    },
    "Status": {
        "closed": "Closed",
        "complete": "Complete",
        "open": "Open",
        "in review": "In Review",
        "in progress": "In Progress",
    },
    "Delay_Category": {
        "mechanical": "Mechanical",
        "mecanical": "Mechanical",
        "weather": "Weather",
        "operational": "Operational",
        "no operator": "No Operator",
        "other": "Other",
    },
    "Activity_Type": {
        "hualing": "Hauling",
        "hauling": "Hauling",
        "loading": "Loading",
        "inspection": "Inspection",
        "break": "Break",
    },
    "Category": {
        "saftey": "Safety",
        "safety": "Safety",
        "ppe": "PPE",
        "vehicle interaction": "Vehicle Interaction",
        "housekeeping": "Housekeeping",
        "procedure": "Procedure",
        "production": "Production",
        "environmental": "Environmental",
    },
    "Severity": {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "critical": "Critical",
    },
    "Notification_Type": {
        "break down": "Breakdown",
        "breakdown": "Breakdown",
        "planned": "Planned",
        "inspection": "Inspection",
    },
    "Direction": {
        "in": "Entry",
        "entry": "Entry",
        "out": "Exit",
        "exit": "Exit",
    },
    "Access_Result": {
        "granted": "Granted",
        "denied": "Denied",
    },
    "Course_Code": {
        "safe-1": "SAFE01",
        "safe01": "SAFE01",
        "eqp02": "EQP02",
        "data01": "DATA01",
    },
}

DATE_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%Y-%m-%d",
]


def load_operational_datasets(file_path, sheet_names=None):
    sheet_names = sheet_names or OPERATIONAL_SHEETS
    workbook_sheets = pd.read_excel(file_path, sheet_name=None)
    return {name: workbook_sheets[name] for name in sheet_names}


def load_rule_catalogue(path=RULE_CATALOGUE_PATH):
    return pd.read_csv(path)


def get_rule(rule_catalogue_df, dataset, column, rule_type=None):
    matches = rule_catalogue_df[
        (rule_catalogue_df["Dataset"].isin([dataset, "All datasets"]))
        & (rule_catalogue_df["Column"].astype(str).str.contains(re.escape(column), regex=True))
    ]

    if rule_type:
        typed_matches = matches[matches["Rule_Type"] == rule_type]
        if not typed_matches.empty:
            matches = typed_matches

    if not matches.empty:
        matches = matches.copy()
        matches["_rank"] = matches.apply(
            lambda row: rank_rule_match(row, rule_type),
            axis=1,
        )
        matches = matches.sort_values(["_rank", "Rule_ID"])

    if matches.empty:
        return {
            "Rule_ID": "CLEANING-NO-CATALOGUE-MATCH",
            "Reason": "No exact rule catalogue match found for this cleaning operation",
            "Rule_Type": rule_type or "Standardisation",
        }

    selected = matches.iloc[0]
    return {
        "Rule_ID": selected["Rule_ID"],
        "Reason": selected["Reason"],
        "Rule_Type": selected["Rule_Type"],
    }


def rank_rule_match(row, requested_rule_type=None):
    if requested_rule_type and row["Rule_Type"] == requested_rule_type:
        return 0

    priority = {
        "Standardisation": 1,
        "Consistency": 2,
        "Validity": 3,
        "Data dictionary guidance": 4,
        "Plausibility": 5,
        "Temporal integrity": 6,
        "Completeness": 7,
        "Privacy": 8,
        "Uniqueness": 9,
    }

    return priority.get(row["Rule_Type"], 99)


def record_transformation(
    log_rows,
    dataset,
    df,
    row_index,
    column,
    original_value,
    new_value,
    rule,
    action_type="AUTO_CORRECT",
):
    if values_equal(original_value, new_value):
        return

    log_rows.append(
        {
            "Dataset": dataset,
            "Source_Row_Index": int(row_index),
            "Source_Row_Number": int(row_index) + 2,
            "Record_ID": get_record_id(dataset, df, row_index),
            "Column": column,
            "Original_Value": original_value,
            "New_Value": new_value,
            "Rule_ID": rule["Rule_ID"],
            "Rule_Type": rule["Rule_Type"],
            "Reason": rule["Reason"],
            "Action_Type": action_type,
            "Review_Status": "AUTO_CORRECT" if action_type == "AUTO_CORRECT" else "AUTO_ACCEPT",
        }
    )


def record_exception(
    exception_rows,
    dataset,
    df,
    row_index,
    column,
    value,
    rule,
    issue_type,
    severity="High",
    recommended_action="Review source evidence before correcting",
):
    exception_rows.append(
        {
            "Exception_ID": f"EXC-{len(exception_rows) + 1:05d}",
            "Dataset": dataset,
            "Source_Row_Index": int(row_index),
            "Source_Row_Number": int(row_index) + 2,
            "Record_ID": get_record_id(dataset, df, row_index),
            "Column": column,
            "Issue_Type": issue_type,
            "Value": value,
            "Rule_ID": rule["Rule_ID"],
            "Severity": severity,
            "Recommended_Action": recommended_action,
            "Status": "REVIEW_REQUIRED",
        }
    )


def values_equal(left, right):
    if pd.isna(left) and pd.isna(right):
        return True
    return str(left) == str(right)


def get_record_id(dataset, df, row_index):
    key_column = PRIMARY_KEYS.get(dataset)

    if key_column in df.columns:
        value = df.at[row_index, key_column]
        if pd.notna(value):
            return value

    return f"{dataset}_row_{int(row_index) + 2}"


def is_text_series(series):
    return series.dtype == "object" or pd.api.types.is_string_dtype(series)


def clean_text_whitespace(dataset, df, rule_catalogue_df, log_rows):
    for column in df.columns:
        if not is_text_series(df[column]):
            continue

        rule = get_rule(rule_catalogue_df, dataset, column, "Validity")

        for row_index, value in df[column].items():
            if pd.isna(value):
                continue

            cleaned_value = str(value).strip()
            record_transformation(
                log_rows,
                dataset,
                df,
                row_index,
                column,
                value,
                cleaned_value,
                rule,
            )
            df.at[row_index, column] = cleaned_value


def canonical_equipment_name(value):
    if pd.isna(value):
        return value

    token = re.sub(r"[^A-Z0-9]", "", str(value).upper())

    patterns = [
        (r"^(TRK|TRUCK)0*(\d+)$", "TRK"),
        (r"^(EXC|EX|EXCAVATOR)0*(\d+)$", "EXC"),
        (r"^(DRL|DRILL)0*(\d+)$", "DRL"),
    ]

    for pattern, prefix in patterns:
        match = re.match(pattern, token)
        if match:
            return f"{prefix}-{int(match.group(2)):03d}"

    word_patterns = [
        (r"^(TRK|TRUCK)([A-Z]+)$", "TRK"),
        (r"^(EXC|EX|EXCAVATOR)([A-Z]+)$", "EXC"),
        (r"^(DRL|DRILL)([A-Z]+)$", "DRL"),
    ]

    for pattern, prefix in word_patterns:
        match = re.match(pattern, token)
        if match and match.group(2) in WORD_NUMBERS:
            return f"{prefix}-{WORD_NUMBERS[match.group(2)]:03d}"

    return str(value)


def standardise_equipment_references(dataset, df, rule_catalogue_df, log_rows):
    for column in EQUIPMENT_REFERENCE_COLUMNS:
        if column not in df.columns:
            continue

        rule = get_rule(rule_catalogue_df, dataset, column, "Consistency")

        for row_index, value in df[column].items():
            new_value = canonical_equipment_name(value)
            record_transformation(
                log_rows,
                dataset,
                df,
                row_index,
                column,
                value,
                new_value,
                rule,
            )
            df.at[row_index, column] = new_value


def standardise_categorical_values(dataset, df, rule_catalogue_df, log_rows):
    for column, mapping in CATEGORY_MAPPINGS.items():
        if column not in df.columns:
            continue

        rule = get_rule(rule_catalogue_df, dataset, column, "Validity")

        for row_index, value in df[column].items():
            if pd.isna(value):
                continue

            mapped_value = mapping.get(str(value).strip().lower(), value)
            record_transformation(
                log_rows,
                dataset,
                df,
                row_index,
                column,
                value,
                mapped_value,
                rule,
            )
            df.at[row_index, column] = mapped_value


def standardise_mobile_numbers(dataset, df, rule_catalogue_df, log_rows):
    if "Mobile_Number" not in df.columns:
        return

    rule = get_rule(rule_catalogue_df, dataset, "Mobile_Number", "Standardisation")

    for row_index, value in df["Mobile_Number"].items():
        if pd.isna(value):
            continue

        normalised_value = re.sub(r"\D", "", str(value))
        record_transformation(
            log_rows,
            dataset,
            df,
            row_index,
            "Mobile_Number",
            value,
            normalised_value,
            rule,
        )
        df.at[row_index, "Mobile_Number"] = normalised_value


def parse_datetime_value(value):
    if pd.isna(value):
        return value, False

    text = str(value).strip()

    for date_format in DATE_FORMATS:
        parsed = pd.to_datetime(text, format=date_format, errors="coerce")
        if pd.notna(parsed):
            if "%H" in date_format or "%I" in date_format:
                return parsed.strftime("%Y-%m-%d %H:%M:%S"), True
            return parsed.strftime("%Y-%m-%d"), True

    parsed = pd.to_datetime(text, errors="coerce")
    if pd.notna(parsed):
        if parsed.hour or parsed.minute or parsed.second:
            return parsed.strftime("%Y-%m-%d %H:%M:%S"), True
        return parsed.strftime("%Y-%m-%d"), True

    return value, False


def date_like_columns(df):
    keywords = [
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

    return [
        column for column in df.columns
        if any(keyword in column.lower() for keyword in keywords)
    ]


def standardise_dates(dataset, df, rule_catalogue_df, log_rows, exception_rows):
    for column in date_like_columns(df):
        rule = get_rule(rule_catalogue_df, dataset, column, "Validity")

        for row_index, value in df[column].items():
            if pd.isna(value):
                continue

            parsed_value, parsed = parse_datetime_value(value)

            if parsed:
                record_transformation(
                    log_rows,
                    dataset,
                    df,
                    row_index,
                    column,
                    value,
                    parsed_value,
                    rule,
                )
                df.at[row_index, column] = parsed_value
            else:
                record_exception(
                    exception_rows,
                    dataset,
                    df,
                    row_index,
                    column,
                    value,
                    rule,
                    "Unparseable date/time",
                )


def convert_units(dataset, df, rule_catalogue_df, log_rows):
    unit_conversions = [
        {
            "unit_column": "Duration_Unit",
            "value_column": "Duration",
            "from_unit": "hours",
            "to_unit": "minutes",
            "factor": 60,
        },
        {
            "unit_column": "Meter_Unit",
            "value_column": "Meter_Reading",
            "from_unit": "mins",
            "to_unit": "hours",
            "factor": 1 / 60,
        },
        {
            "unit_column": "Fuel_Unit",
            "value_column": "Fuel_Used",
            "from_unit": "gallons",
            "to_unit": "litres",
            "factor": 3.78541,
        },
    ]

    for conversion in unit_conversions:
        unit_column = conversion["unit_column"]
        value_column = conversion["value_column"]

        if unit_column not in df.columns or value_column not in df.columns:
            continue

        df[value_column] = df[value_column].astype("float64")

        unit_rule = get_rule(rule_catalogue_df, dataset, unit_column, "Consistency")
        value_rule = get_rule(rule_catalogue_df, dataset, value_column, "Consistency")

        for row_index, unit_value in df[unit_column].items():
            if pd.isna(unit_value):
                continue
            if str(unit_value).strip().lower() != conversion["from_unit"]:
                continue

            original_measure = df.at[row_index, value_column]
            new_measure = original_measure
            if pd.notna(original_measure):
                new_measure = round(float(original_measure) * conversion["factor"], 4)

            record_transformation(
                log_rows,
                dataset,
                df,
                row_index,
                value_column,
                original_measure,
                new_measure,
                value_rule,
            )
            record_transformation(
                log_rows,
                dataset,
                df,
                row_index,
                unit_column,
                unit_value,
                conversion["to_unit"],
                unit_rule,
            )

            df.at[row_index, value_column] = new_measure
            df.at[row_index, unit_column] = conversion["to_unit"]


def remove_exact_duplicates(dataset, df, rule_catalogue_df, log_rows):
    duplicate_mask = df.duplicated(keep="first")

    if not duplicate_mask.any():
        return df

    rule = get_rule(rule_catalogue_df, dataset, "Entire row", "Uniqueness")

    for row_index in df.index[duplicate_mask]:
        record_transformation(
            log_rows,
            dataset,
            df,
            row_index,
            "Entire row",
            "Duplicate row retained in raw source",
            "Excluded from cleaned dataset",
            rule,
            action_type="EXCLUDE_DUPLICATE_ROW",
        )

    return df.loc[~duplicate_mask].copy()


def flag_missing_values(dataset, df, rule_catalogue_df, exception_rows):
    for column in df.columns:
        if not df[column].isna().any():
            continue

        rule = get_rule(rule_catalogue_df, dataset, column, "Completeness")

        for row_index, value in df.loc[df[column].isna(), column].items():
            record_exception(
                exception_rows,
                dataset,
                df,
                row_index,
                column,
                value,
                rule,
                "Missing value",
                severity="Medium",
                recommended_action="Confirm whether missingness is valid before trusted analysis",
            )


def flag_numeric_issues(dataset, df, rule_catalogue_df, exception_rows):
    for column in df.select_dtypes(include="number").columns:
        rule = get_rule(rule_catalogue_df, dataset, column, "Plausibility")

        negative_mask = df[column] < 0
        for row_index, value in df.loc[negative_mask, column].items():
            record_exception(
                exception_rows,
                dataset,
                df,
                row_index,
                column,
                value,
                rule,
                "Negative numeric value",
            )

        if "pct" in column.lower() or "%" in column:
            pct_mask = (df[column] < 0) | (df[column] > 1)
            for row_index, value in df.loc[pct_mask, column].items():
                record_exception(
                    exception_rows,
                    dataset,
                    df,
                    row_index,
                    column,
                    value,
                    rule,
                    "Percentage outside expected 0 to 1 range",
                )

        if column.lower() == "score":
            score_mask = (df[column] < 0) | (df[column] > 100)
            for row_index, value in df.loc[score_mask, column].items():
                record_exception(
                    exception_rows,
                    dataset,
                    df,
                    row_index,
                    column,
                    value,
                    rule,
                    "Score outside 0 to 100 range",
                )


def flag_temporal_issues(dataset, df, rule_catalogue_df, exception_rows):
    temporal_pairs = [
        ("Delays_Downtime", "Start_Time", "End_Time"),
        ("Operator_Activities", "Activity_Start", "Activity_End"),
        ("Safety_Observations", "Observation_Date", "Closed_Date"),
        ("Training_Records", "Completion_Date", "Expiry_Date"),
        ("Maintenance_Notifications", "Actual_Start", "Actual_End"),
        ("Environmental_Readings", "Reading_Time", "Calibration_Due"),
    ]

    for pair_dataset, start_column, end_column in temporal_pairs:
        if dataset != pair_dataset:
            continue
        if start_column not in df.columns or end_column not in df.columns:
            continue

        rule = get_rule(rule_catalogue_df, dataset, f"{start_column}|{end_column}", "Temporal integrity")
        start_values = pd.to_datetime(df[start_column], errors="coerce")
        end_values = pd.to_datetime(df[end_column], errors="coerce")
        contradiction_mask = start_values.notna() & end_values.notna() & (end_values < start_values)

        for row_index in df.index[contradiction_mask]:
            record_exception(
                exception_rows,
                dataset,
                df,
                row_index,
                f"{start_column}|{end_column}",
                f"{df.at[row_index, start_column]} -> {df.at[row_index, end_column]}",
                rule,
                "Temporal contradiction",
                severity="Critical",
            )


def build_standardization_gap_report(cleaned_datasets):
    gap_rows = []

    for dataset, df in cleaned_datasets.items():
        for column in EQUIPMENT_REFERENCE_COLUMNS:
            if column not in df.columns:
                continue

            for row_index, value in df[column].items():
                if pd.isna(value) or str(value).strip() == "":
                    continue

                expected_value = canonical_equipment_name(value)
                current_value = str(value)
                canonical_pattern = r"^(TRK|EXC|DRL)-\d{3}$"

                if current_value != expected_value:
                    gap_rows.append(
                        {
                            "Dataset": dataset,
                            "Source_Row_Index": int(row_index),
                            "Source_Row_Number": int(row_index) + 2,
                            "Record_ID": get_record_id(dataset, df, row_index),
                            "Column": column,
                            "Current_Value": current_value,
                            "Expected_Value": expected_value,
                            "Gap_Type": "Known equipment alias still present",
                            "Severity": "High",
                            "Recommended_Action": "Apply equipment reference standardisation before reconciliation",
                        }
                    )
                elif not re.match(canonical_pattern, current_value):
                    gap_rows.append(
                        {
                            "Dataset": dataset,
                            "Source_Row_Index": int(row_index),
                            "Source_Row_Number": int(row_index) + 2,
                            "Record_ID": get_record_id(dataset, df, row_index),
                            "Column": column,
                            "Current_Value": current_value,
                            "Expected_Value": "",
                            "Gap_Type": "Unrecognised equipment reference format",
                            "Severity": "Medium",
                            "Recommended_Action": "Review whether this value needs a new domain alias rule",
                        }
                    )

        for column, mapping in CATEGORY_MAPPINGS.items():
            if column not in df.columns:
                continue

            for row_index, value in df[column].items():
                if pd.isna(value):
                    continue

                current_value = str(value).strip()
                expected_value = mapping.get(current_value.lower())
                if expected_value and current_value != expected_value:
                    gap_rows.append(
                        {
                            "Dataset": dataset,
                            "Source_Row_Index": int(row_index),
                            "Source_Row_Number": int(row_index) + 2,
                            "Record_ID": get_record_id(dataset, df, row_index),
                            "Column": column,
                            "Current_Value": current_value,
                            "Expected_Value": expected_value,
                            "Gap_Type": "Known categorical alias still present",
                            "Severity": "Medium",
                            "Recommended_Action": "Apply categorical standardisation before trusted use",
                        }
                    )

    return pd.DataFrame(
        gap_rows,
        columns=[
            "Dataset",
            "Source_Row_Index",
            "Source_Row_Number",
            "Record_ID",
            "Column",
            "Current_Value",
            "Expected_Value",
            "Gap_Type",
            "Severity",
            "Recommended_Action",
        ],
    )


def clean_dataset(dataset, raw_df, rule_catalogue_df, log_rows, exception_rows):
    cleaned_df = raw_df.copy()

    clean_text_whitespace(dataset, cleaned_df, rule_catalogue_df, log_rows)
    standardise_equipment_references(dataset, cleaned_df, rule_catalogue_df, log_rows)
    standardise_categorical_values(dataset, cleaned_df, rule_catalogue_df, log_rows)
    standardise_mobile_numbers(dataset, cleaned_df, rule_catalogue_df, log_rows)
    standardise_dates(dataset, cleaned_df, rule_catalogue_df, log_rows, exception_rows)
    convert_units(dataset, cleaned_df, rule_catalogue_df, log_rows)
    flag_missing_values(dataset, cleaned_df, rule_catalogue_df, exception_rows)
    flag_numeric_issues(dataset, cleaned_df, rule_catalogue_df, exception_rows)
    flag_temporal_issues(dataset, cleaned_df, rule_catalogue_df, exception_rows)
    cleaned_df = remove_exact_duplicates(dataset, cleaned_df, rule_catalogue_df, log_rows)

    return cleaned_df


def run_cleaning(datasets, rule_catalogue_path=RULE_CATALOGUE_PATH, output_dir=OUTPUT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rule_catalogue_df = load_rule_catalogue(rule_catalogue_path)
    cleaned_datasets = {}
    log_rows = []
    exception_rows = []
    summary_rows = []

    for dataset, raw_df in datasets.items():
        cleaned_df = clean_dataset(
            dataset,
            raw_df,
            rule_catalogue_df,
            log_rows,
            exception_rows,
        )

        cleaned_datasets[dataset] = cleaned_df
        cleaned_df.to_csv(output_dir / f"{dataset}_cleaned.csv", index=False)

        summary_rows.append(
            {
                "Dataset": dataset,
                "Raw_Rows": len(raw_df),
                "Cleaned_Rows": len(cleaned_df),
                "Rows_Removed": len(raw_df) - len(cleaned_df),
            }
        )

    transformation_log_df = pd.DataFrame(log_rows)
    exception_candidates_df = pd.DataFrame(exception_rows)
    cleaning_summary_df = pd.DataFrame(summary_rows)

    if not transformation_log_df.empty:
        transformation_counts = (
            transformation_log_df.groupby("Dataset")
            .size()
            .rename("Transformation_Count")
            .reset_index()
        )
        cleaning_summary_df = cleaning_summary_df.merge(
            transformation_counts,
            on="Dataset",
            how="left",
        )
    else:
        cleaning_summary_df["Transformation_Count"] = 0

    if not exception_candidates_df.empty:
        exception_counts = (
            exception_candidates_df.groupby("Dataset")
            .size()
            .rename("Exception_Candidate_Count")
            .reset_index()
        )
        cleaning_summary_df = cleaning_summary_df.merge(
            exception_counts,
            on="Dataset",
            how="left",
        )
    else:
        cleaning_summary_df["Exception_Candidate_Count"] = 0

    cleaning_summary_df = cleaning_summary_df.fillna(0)
    cleaning_summary_df["Transformation_Count"] = cleaning_summary_df[
        "Transformation_Count"
    ].astype(int)
    cleaning_summary_df["Exception_Candidate_Count"] = cleaning_summary_df[
        "Exception_Candidate_Count"
    ].astype(int)

    standardization_gap_report_df = build_standardization_gap_report(cleaned_datasets)

    transformation_log_df.to_csv(output_dir / "transformation_log.csv", index=False)
    exception_candidates_df.to_csv(output_dir / "exception_candidates.csv", index=False)
    cleaning_summary_df.to_csv(output_dir / "cleaning_summary.csv", index=False)
    standardization_gap_report_df.to_csv(
        output_dir / "standardization_gap_report.csv",
        index=False,
    )

    return {
        "cleaned_datasets": cleaned_datasets,
        "transformation_log": transformation_log_df,
        "exception_candidates": exception_candidates_df,
        "cleaning_summary": cleaning_summary_df,
        "standardization_gap_report": standardization_gap_report_df,
    }
