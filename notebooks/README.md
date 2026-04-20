# Notebooks

Seven notebooks covering audit, EDA, four nested models, and cross-model comparison.

## Order of execution

1. `audit.ipynb` — exclusions investigation over `modeling_df.parquet`.
2. `eda.ipynb` — Phase 4 EDA: outcome, demographics, and detector-quality figures.
3. `model_1.ipynb` — fully pooled likelihood; Normal then Student-t.
4. `model_2.ipynb` — subject-level partial pooling: Student-t cohort sigma (M2) plus per-subject-sigma ablations (M2a, M2b).
5. `model_3.ipynb` — sex as group-level predictor on the M2b template.
6. `model_4.ipynb` — sex plus standardized leg length, IAD, and mass.
7. `model_comparison.ipynb` — trial- and subject-grain `az.compare`, cross-model parameter summary, headline forest, PPC overlay.

The four model notebooks run independently with `modeling_df.parquet`. `modeling_df.parquet` is an asset created by downloading the data and proccessing it with `bin/build.sh`, but a frozen reference is also committed to `data/reference/modeling_df.parquet`. `model_comparison.ipynb` requires all seven `idata_*.nc` files in `data/processed/`.

## Input: modeling_df.parquet (processed vs reference)

Every notebook's setup cell reads a flattened trial-level DataFrame with a two-path fallback:

- `data/processed/modeling_df.parquet` — produced by `bin/build.sh`. Gitignored. The canonical path.
- `data/reference/modeling_df.parquet` — committed frozen reference. Used when `bin/build.sh` was not run.

The setup cell prefers `processed`, falls back to `reference`.

## Outputs per notebook

### audit.ipynb

Writes to `model_assets/audit/`.

| filename | kind | description |
|---|---|---|
| exclusions_headline.csv | csv | overall and sex-level exclusion scalars |
| exclusions_by_reason.csv | csv | counts by qc_flag family |
| exclusions_pipeline_error_subtypes.csv | csv | breakdown of `pipeline_error:*` flags |
| exclusions_by_sex.csv | csv | counts and rates by sex |
| exclusions_by_speed.csv | csv | counts and rates by speed |
| exclusions_by_sex_speed.csv | csv | sex × speed crosstab with hot-cell flag |
| exclusions_by_subject.csv | csv | per-subject exclusion counts and rates |
| exclusions_reason_by_sex.csv | csv | reason × sex crosstab |
| exclusions_high_rate_subjects.csv | csv | subjects with exclusion rate > 10% |

### eda.ipynb

Writes to `model_assets/eda/`.

| filename | kind | description |
|---|---|---|
| eda_outcome_distribution.png | figure | cadence_error overall and by sex × speed |
| anthropometrics_by_sex.png | figure | leg length, IAD, mass distributions by sex |
| error_vs_cadence_by_speed.png | figure | cadence_error vs cadence_plate by speed |
| exclusion_rate_by_sex.png | figure | exclusion rates faceted by sex |
| detector_vs_truth.png | figure | IMU cadence vs plate cadence scatter |
| per_subject_undercount.png | figure | per-subject IMU undercount rate |

### model_1.ipynb

Writes to `model_assets/model_1/`, plus one pairwise-LOO CSV (`compare_pairwise_m1_vs_m1t.csv`) to `model_assets/model_comparison/`.

| filename | kind | description |
|---|---|---|
| model_1_dag.png | figure | Model 1 (Normal) graphical model |
| model_1_trace.png | figure | trace plot, Model 1 |
| model_1_rank.png | figure | rank plot, Model 1 |
| model_1_ppc.png | figure | posterior predictive, Model 1 |
| model_1t_dag.png | figure | Model 1-t (Student-t) graphical model |
| model_1t_trace.png | figure | trace plot, Model 1-t |
| model_1t_rank.png | figure | rank plot, Model 1-t |
| model_1t_ppc.png | figure | posterior predictive, Model 1-t |
| model_1_summary.csv | csv | `az.summary` for Model 1 |
| model_1t_summary.csv | csv | `az.summary` for Model 1-t |
| model_1_loo_pointwise.csv | csv | per-observation LOO, Model 1 |
| model_1_loo_headline.csv | csv | LOO scalars (elpd, se, p_loo), Model 1 |
| model_1t_loo_pointwise.csv | csv | per-observation LOO, Model 1-t |
| model_1t_loo_headline.csv | csv | LOO scalars, Model 1-t |

Serializes `idata_model_1.nc` and `idata_model_1t.nc` to `data/processed/`.

### model_2.ipynb

Writes to `model_assets/model_2/`.

| filename | kind | description |
|---|---|---|
| model_2_dag.png | figure | Model 2 graphical model |
| model_2_prior_predictive.png | figure | prior predictive, Model 2 |
| model_2_trace.png | figure | trace plot, Model 2 |
| model_2_rank.png | figure | rank plot, Model 2 |
| model_2_alpha_subject_caterpillar.png | figure | per-subject intercept caterpillar |
| model_2_ppc.png | figure | posterior predictive, Model 2 |
| model_2_per_subject_ppc.png | figure | per-subject PPC tail coverage |
| model_2a_dag.png | figure | Model 2a graphical model |
| model_2b_dag.png | figure | Model 2b graphical model |
| model_2a_trace.png | figure | trace plot, Model 2a |
| model_2a_rank.png | figure | rank plot, Model 2a |
| model_2b_trace.png | figure | trace plot, Model 2b |
| model_2b_rank.png | figure | rank plot, Model 2b |
| model_2b_ppc.png | figure | posterior predictive, Model 2b |
| model_2_summary.csv | csv | `az.summary` for Model 2 |
| model_2a_summary.csv | csv | `az.summary` for Model 2a |
| model_2b_summary.csv | csv | `az.summary` for Model 2b |
| model_2_loo_pointwise.csv | csv | per-observation LOO, Model 2 |
| model_2_loo_headline.csv | csv | LOO scalars, Model 2 |
| model_2a_loo_pointwise.csv | csv | per-observation LOO, Model 2a |
| model_2a_loo_headline.csv | csv | LOO scalars, Model 2a |
| model_2b_loo_pointwise.csv | csv | per-observation LOO, Model 2b |
| model_2b_loo_headline.csv | csv | LOO scalars, Model 2b |

Serializes `idata_model_2.nc`, `idata_model_2a.nc`, `idata_model_2b.nc` to `data/processed/`.

### model_3.ipynb

Writes to `model_assets/model_3/`.

| filename | kind | description |
|---|---|---|
| model_3_dag.png | figure | Model 3 graphical model |
| model_3_ppc.png | figure | posterior predictive, Model 3 vs 2b |
| model_3_trace.png | figure | trace plot, Model 3 |
| model_3_rank.png | figure | rank plot, Model 3 |
| model_3_forest_alpha_sex.png | figure | `alpha_sex` forest |
| model_3_summary.csv | csv | `az.summary` for Model 3 |
| model_3_loo_pointwise.csv | csv | per-observation LOO, Model 3 |
| model_3_loo_headline.csv | csv | LOO scalars, Model 3 |

Serializes `idata_model_3.nc` to `data/processed/`.

### model_4.ipynb

Writes to `model_assets/model_4/`.

| filename | kind | description |
|---|---|---|
| model_4_dag.png | figure | Model 4 graphical model |
| model_4_ppc_three_way.png | figure | posterior predictive, Model 4 |
| model_4_trace.png | figure | trace plot, Model 4 |
| model_4_rank.png | figure | rank plot, Model 4 |
| model_4_demographic_forest.png | figure | sex + anthropometric effects forest |
| model_4_summary.csv | csv | `az.summary` for Model 4 |
| model_4_loo_pointwise.csv | csv | per-observation LOO, Model 4 |
| model_4_loo_headline.csv | csv | LOO scalars, Model 4 |
| model_4_anthropometric_correlations.csv | csv | pairwise correlations among standardized predictors |

Serializes `idata_model_4.nc` to `data/processed/`.

### model_comparison.ipynb

Writes to `model_assets/model_comparison/`.

| filename | kind | description |
|---|---|---|
| compare_trial_grain.csv | csv | `az.compare` across all seven fits, trial grain |
| compare_subject_grain.csv | csv | `az.compare` across all seven fits, subject grain |
| cross_model_parameter_summary.csv | csv | common-parameter summary across models |
| demographic_effects_forest.png | figure | headline forest of demographic effects |
| ppc_overlay_m1_m1t_m2_m2b.png | figure | PPC ECDF overlay across likelihood variants |
| sampling_diagnostics.csv | csv | divergences, ESS, R-hat summary per model |
| subject_grain_pareto_k_maxes.csv | csv | per-model max Pareto-k at subject grain |

## Data directory outputs

`bin/build.sh` writes `data/processed/modeling_df.parquet` and `data/scout/n_strikes_distribution.parquet`. Model notebooks write `data/processed/idata_model_{N}.nc`. All are gitignored.
