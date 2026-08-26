# Operational Data Modelling

## Task 1 Progress Summary

Task 1 is focused on building a trustworthy operational data foundation before any cleaning or standardisation is applied. The current workflow follows this sequence:

```text
PHASE 1 - INVENTORY & PROFILING
PHASE 1.5 - DATA QUALITY RULE CATALOGUE
PHASE 2 - CLEANING & STANDARDISATION
PHASE 3 - RECONCILIATION
PHASE 4 - EXCEPTION REGISTER
PHASE 5 - VALIDATION & TRUST ASSESSMENT
```

The project has completed Phase 1 inventory/profiling and now has an initial Phase 1.5 data quality rule catalogue ready to drive Phase 2 cleaning.

## Completed In Phase 1

The current `Task_1_Package/data_extraction.ipynb` notebook extracts and profiles the operational workbook:

```text
Task_1_Package/data/raw/Operational_Mining_Data.xlsx
```

The following 9 operational sheets were inventoried:

1. Equipment_Events
2. Delays_Downtime
3. Operator_Activities
4. Shift_Performance
5. Safety_Observations
6. Training_Records
7. Maintenance_Notifications
8. Environmental_Readings
9. Access_Control

The notebook also inspects the `Data_Dictionary` sheet so the next phase can define data quality rules before changing source values.

## Generated Inventory Outputs

The profiling outputs are saved in:

```text
Task_1_Package/data_inventory/
```

Current inventory files:

1. `dataset_shapes.csv`
2. `datasheet_Highlevel_inventory.csv`
3. `datasheet-column-level.csv`
4. `missing-value_profile.csv`
5. `identifier_columns.csv`
6. `Free-text_inventory.csv`
7. `privacy_sensitive_fields.csv`
8. `data_dictionary.csv`
9. `data_quality_rule_catalogue.csv`
10. `rule_domain_overrides.csv`
11. `Equipment_Events_numeric_profile.csv`
12. `Delays_Downtime_numeric_profile.csv`
13. `Operator_Activities_numeric_profile.csv`
14. `Shift_Performance_numeric_profile.csv`
15. `Training_Records_numeric_profile.csv`
16. `Maintenance_Notifications_numeric_profile.csv`
17. `Environmental_Readings_numeric_profile.csv`

## High-Level Profiling Results

Each operational dataset currently contains 46 rows. Duplicate rows were detected in every operational sheet, with 1 duplicate row per sheet.

Missing-value profiling found:

| Dataset | Rows | Columns | Duplicate Rows | Missing Values | Missing % |
|---|---:|---:|---:|---:|---:|
| Equipment_Events | 46 | 11 | 1 | 16 | 3.16 |
| Delays_Downtime | 46 | 11 | 1 | 26 | 5.14 |
| Operator_Activities | 46 | 15 | 1 | 7 | 1.01 |
| Shift_Performance | 46 | 15 | 1 | 8 | 1.16 |
| Safety_Observations | 46 | 13 | 1 | 63 | 10.54 |
| Training_Records | 46 | 14 | 1 | 15 | 2.33 |
| Maintenance_Notifications | 46 | 14 | 1 | 1 | 0.16 |
| Environmental_Readings | 46 | 11 | 1 | 23 | 4.55 |
| Access_Control | 46 | 12 | 1 | 16 | 2.90 |

## Data Quality Signals Found

The profiling phase identified early quality signals that should become formal rules before cleaning:

1. Identifier columns exist across all major sheets, including event IDs, operator IDs, badge IDs, employee IDs, notification IDs, work order IDs, sensor IDs, and access event IDs.
2. Equipment names appear in multiple inconsistent formats, such as `TRK002`, `TRK-003`, `truck03`, `Truck 3`, `EX 001`, and `Excavator 1`.
3. Category values need standardisation, including case differences and spelling errors such as `Saftey`, `Mecanical`, `mechanical`, `break down`, and `Breakdown`.
4. Date and time fields appear in mixed formats across operational sheets.
5. Numeric profiling identified values requiring review, including negative durations or downtime, extreme meter readings, high scores, and outlier environmental readings.
6. Unit fields require rule-based handling before comparison, including minutes vs hours, litres vs gallons, and mixed environmental units.
7. Privacy-sensitive fields were identified, including names, emails, mobile numbers, home zones, badge IDs, employee IDs, operator IDs, medical fitness codes, and free-text comments/descriptions.

## Phase 1.5 Rule Catalogue

The profile findings and `Data_Dictionary` guidance have been converted into a programmatically generated Project Signal Data Quality Rule Catalogue:

```text
Task_1_Package/data_inventory/data_quality_rule_catalogue.csv
Task_1_Package/data_quality_rule_catalogue.ipynb
Task_1_Package/rule_catalogue_generator.py
```

The catalogue is generated from the existing profiling outputs rather than manually typed into the notebook. Human judgement rules can be added to:

```text
Task_1_Package/data_inventory/rule_domain_overrides.csv
```

The catalogue currently contains 200 rules and uses these columns:

```text
Rule_ID
Dataset
Column
Rule_Type
Valid_Condition
Action
Auto_Correct_Allowed
Severity
Reason
Rule_Source
Evidence
```

Rule coverage summary:

| Rule Type | Rule Count |
|---|---:|
| Completeness | 28 |
| Consistency | 5 |
| Data dictionary guidance | 20 |
| Plausibility | 14 |
| Privacy | 24 |
| Temporal integrity | 6 |
| Uniqueness | 19 |
| Validity | 84 |

The catalogue separates rules that can be auto-corrected from rules that must be flagged. Current status:

| Auto Correct Allowed | Rule Count |
|---|---:|
| TRUE | 67 |
| FALSE | 133 |

Rules should define:

1. What values are valid.
2. What can be safely auto-corrected.
3. What must be flagged for review.
4. What should be excluded from trusted analysis.
5. What requires cross-dataset reconciliation.

Current rule dimensions:

1. Completeness
2. Uniqueness
3. Validity
4. Consistency
5. Temporal integrity
6. Referential integrity
7. Plausibility
8. Reconciliation
9. Privacy
10. Lineage

## Cleaning Approach

Cleaning should not happen until the rule catalogue defines what clean means for each field.

Target cleaning actions:

1. Standardise known equivalent values, such as equipment aliases and categorical labels.
2. Correct obvious semantic errors only when supported by the rule catalogue.
3. Derive values from source evidence where appropriate, such as duration from start and end timestamps.
4. Flag exceptions where values look invalid but cannot be safely corrected.
5. Exclude records only when they are unusable or would create misleading analysis.

The project should preserve three versions throughout:

```text
RAW
STANDARDISED / CLEANED
VALIDATED / TRUSTED
```

Each transformation should be traceable through an exception or transformation log.

## Human Review Status Categories

The exception workflow should support these review outcomes:

1. `AUTO_ACCEPT`
2. `AUTO_CORRECT`
3. `REVIEW_REQUIRED`
4. `REJECT`
5. `UNRESOLVED`

## Next Work

The immediate next task is Phase 2: build the cleaning and standardisation engine using the rule catalogue. That phase should produce cleaned datasets plus a transformation log that answers what changed, why it changed, which rule caused it, and whether the change was automatic or reviewed.
