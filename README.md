-- Active: 1784713241693@@127.0.0.1@3306
# We first start by visually exploring the base/raw dataset.

```
Noticed PK Derivation: Equipment_Name -> Equipment_ID
```

## Our first step is to do a data inventory to better understand our data:
-> Assumed Realtionship Catalogue:
---
* Operational activities
* Shift performance - monitor worked shifts,date and equipment utilization
* Training Records - tracks artisan training courses and student information and results
* Safety Observations - operational safety across the workplace
* Access Control - monitor access across the operational workplace

-> Equipment related records:
---
* Equipment Events - equipment availibility and usage
* Delays Downtime - tracks equipment utilisation with regards to hindered operations
* Maintenance Notification - monitors equiptment maintenance
* Shift performance - tracks utilization pct of equiptment and availability

---

```
Environmental Readings - focus on the conditions on the day (doesn't fall under any of the top catalogues, no operations occured due to these readings)
```

---
## Data Quality Rule Catalogue:
Using the extractions from the supplied problem list

1. Completeness
2. Uniqueness
Validity
Consistency
Temporal integrity
Referential integrity
Plausibility 
Reconciliation
Privacy
Lineage

## Exception Registry
| Exception_id | EXC-00031 |

| dataset | Equipment Events |

## Target Approach to data_cleaning
1. Standardize - TRK002 -> TRK-002 , truck02 -> TRK-002, Truck 2 -> TRK-002, granted -> Granted, 2026/07/01 11:00:00 -> 2026/07/01 - 11:00, 082-555-0102 -> 082550102
2. Semantic Corrections -  Saftey -> Safety, Housekeeping -> House Keeping, mecanical -> Mechanical
3. Derive - duration = end_time - start_time, 
4. flag - duration = -42 
5. Exclude - avoid using unusable records because they create too much noise for our analysis

## Human Review acceptance criteria
AUTO_ACCEPT
AUTO_CORRECT
REVIEW_REQUIRED
REJECT
UNRESOLVED

## Reconciliation Cross-Validation