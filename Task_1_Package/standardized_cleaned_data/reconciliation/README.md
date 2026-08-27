# Reconciliation

This folder contains Phase 3 reconciliation outputs generated from the cleaned operational datasets.

Current files:

1. `reconciliation_findings.csv`
2. `reconciliation_summary.csv`
3. `reconciliation_dataset_summary.csv`
4. `reconciliation_check_summary.csv`
5. `reconciliation_validation_summary.csv`

The checks look for referential integrity issues, profile conflicts, equipment/event conflicts, and operator/activity conflicts before the findings are consolidated into the exception register.

The latest targeted run produced 20 reconciliation findings after upstream equipment-reference standardisation was widened. `Related_Record_ID` is populated for matched conflict records and set to `NO_MATCH_FOUND` for true referential integrity gaps.
