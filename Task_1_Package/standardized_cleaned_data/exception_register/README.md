# Exception Register

This folder contains the reviewable exception register generated from `standardized_cleaned_data/exception_candidates.csv`, transformation-log validation issues, and Phase 3 reconciliation findings.

Current files:

1. `exception_register.csv`
2. `exception_register_summary.csv`
3. `exception_register_dataset_summary.csv`
4. `exception_register_issue_type_summary.csv`
5. `exception_priority_queue.csv`
6. `exception_register_validation_summary.csv`

The register preserves source evidence and adds review fields for priority, owner, trusted-data guidance, decision, resolution value, and resolution notes.

The latest targeted run produced 299 register rows and 124 priority queue rows after reconciliation findings were added.
