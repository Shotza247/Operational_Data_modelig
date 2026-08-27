# Phase 2 Standardized/Cleaned Data

This folder is reserved for Phase 2 outputs generated from the raw operational workbook using the Phase 1.5 data quality rule catalogue.

Current outputs:

1. `Equipment_Events_cleaned.csv`
2. `Delays_Downtime_cleaned.csv`
3. `Operator_Activities_cleaned.csv`
4. `Shift_Performance_cleaned.csv`
5. `Safety_Observations_cleaned.csv`
6. `Training_Records_cleaned.csv`
7. `Maintenance_Notifications_cleaned.csv`
8. `Environmental_Readings_cleaned.csv`
9. `Access_Control_cleaned.csv`
10. `transformation_log.csv`
11. `exception_candidates.csv`
12. `cleaning_summary.csv`
13. `standardization_gap_report.csv`
14. `transformation_logging/`
15. `reconciliation/`
16. `exception_register/`

Phase 2 currently removes one duplicate row from each operational dataset, leaving 45 cleaned rows per dataset. The transformation log contains 1044 automatically recorded changes. The exception candidate file contains 279 records that were flagged for review rather than silently corrected. The standardization gap report currently contains 0 rows.

Transformation-log review outputs are saved in `transformation_logging/`. The latest targeted run produced 6 validation checks, 0 validation issues, 9 dataset summaries, 49 rule summaries, and 0 transformation review queue rows.

Reconciliation outputs are saved in `reconciliation/`. The latest targeted run produced 20 reconciliation findings, 10 critical findings, 10 high-severity findings, and 0 validation failures.

Exception-register outputs are saved in `exception_register/`. The latest targeted run produced 299 register rows, 124 priority queue rows, 5 validation checks, and 0 validation failures after reconciliation findings were added.

Cleaning actions currently include:

1. Equipment-name and equipment-reference standardisation.
2. Controlled category casing and typo standardisation.
3. Date/time standardisation into ISO-style values.
4. Mobile-number format standardisation.
5. Supported unit conversions.
6. Exact duplicate row removal after logging.
7. Missing, implausible, and contradictory values flagged for review.

The cleaning workflow should use:

```text
Task_1_Package/data_inventory/data_quality_rule_catalogue.csv
Task_1_Package/rule_catalogue_generator.py
Task_1_Package/cleaning_standardization.py
Task_1_Package/transformation_logging.py
Task_1_Package/reconciliation.py
Task_1_Package/exception_register.py
```

Do not place raw data or profiling inventory files in this folder.
