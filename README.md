# Wearable Calibration Bayes

*By [Michelle Griffith](https://www.linkedin.com/in/michellemgriffith/). Final project
for ISyE 6420 (Bayesian Statistics), Georgia Tech, Spring 2026.*

A hierarchical Bayesian audit of whether a generic step-counting algorithm produces
systematically biased cadence estimates across demographic groups, using the Kuopio
Gait Dataset as a lab-grade reference.

## Motivation

Consumer wearables count steps by applying a threshold to accelerometer data from a
single body-worn sensor. That threshold is calibrated to the acceleration amplitudes
produced by a "typical" stride. Smaller-statured people produce smaller acceleration
peaks because stride dynamics scale with body geometry, so a universal threshold may
miss more steps for them. Because bodies are sexed, this geometric bias lands
asymmetrically on women. This is the *Invisible Women* thesis [Criado Perez, 2019]
expressed as a testable claim about a specific algorithm class. I wear an Oura ring
daily, which is what made the question concrete enough to want to answer with a model
rather than a hunch.

Prior work points in the direction without resolving it. Crouter et al. (2005) showed
that pedometer accuracy degrades with body mass index. Sequeira et al. (1995) reported
sex-disaggregated step counts in a large population survey without modeling the
measurement process. Rowe et al. (2011) established that walking cadence varies by
more than 20 steps per minute across the adult height range, which sets a clear
mechanistic prior: if body size matters at all, the effect should be visible.
Straczkiewicz et al. (2023) called their own classifier "one-size-fits-most," an
honest acknowledgement that subgroup performance is open. None of these studies puts
a credible interval on a demographic effect on algorithm error against motion-capture
ground truth, with body geometry decomposed into measured covariates. Hierarchical
Bayesian partial pooling is the right tool for that question: it borrows strength
across subjects, handles a 17F/30M imbalance honestly, and produces posterior
credible intervals rather than yes/no hypothesis tests.

I chose this as a portfolio project. I'm interested in data science for health
biometrics — movement data in particular — and wanted hands-on experience with
a dataset that pairs wearable-grade IMU signals with lab-grade optical
motion-capture and force-plate ground truth.

## What's in this repo

- `bin/` — shell entry points for environment setup, data download, and the build
  pipeline (`install.sh`, `download_data.sh`, `build.sh`, `setup.sh`)
- `src/` — Python modules that do the actual data extraction and modeling-DataFrame
  assembly (`download_kuopio.py`, `imu.py`, `ground_truth.py`, `build_modeling_df.py`,
  `build_scout_assets.py`)
- `notebooks/` — seven analysis notebooks covering EDA, exclusions audit, four
  nested Bayesian models, and cross-model comparison; see
  [`notebooks/README.md`](notebooks/README.md) for execution order and per-notebook
  asset tables
- `data/` — participant anthropometrics (`info_participants.xlsx`), the dataset
  description (`dataset_info.md`), and a committed frozen reference
  (`reference/modeling_df.parquet`) so the notebooks run without re-downloading
  the raw data
- `report/` — final writeup (`wearable_calibration_bayes_report.pdf`) and
  supporting appendix CSVs
- `tests/` — unit tests for the build pipeline
- `config.yaml`, `environment.yaml` — pipeline configuration and the pinned conda
  environment spec

## How to interact

There are two entry points. Both assume you have `conda` available and are run from
the project root.

### Run the notebooks against the committed frozen reference

This is the fastest way to see the analysis. Every notebook reads
`data/processed/modeling_df.parquet` if present and otherwise falls back to the
committed frozen reference at `data/reference/modeling_df.parquet`, so the analysis
runs end-to-end without the ~23 GB raw download.

```bash
bin/install.sh                              # create the conda env (idempotent)
conda activate wearable-calibration-bayes   # must be done in your shell
# open notebooks/ and run top-to-bottom; see notebooks/README.md for order
```

The model notebooks serialize `idata_model_*.nc` to `data/processed/` and write
figures and summary CSVs under `notebooks/model_assets/`. Both directories are
gitignored — they are regenerated locally on every run.

### Download the raw data and rebuild the modeling DataFrame from source

```bash
bin/install.sh                              # create the conda env (idempotent)
conda activate wearable-calibration-bayes   # must be done in your shell
bin/download_data.sh                        # fetch ~23 GB from Zenodo, idempotent
bin/build.sh                                # write data/processed/modeling_df.parquet
```

`bin/setup.sh` chains the download and build steps into a single command once the
env is active. Every script captures stdout and stderr to
`logs/<script>.{stdout,stderr}.log` on every run.

**Download time.** The Kuopio dataset is split into three Zenodo archives (~23 GB
combined) that download in parallel — three jobs by default; override with
`bin/download_data.sh --jobs N`. Zenodo throttles per-connection, so a single
stream typically runs at 1–3 MB/s while three parallel streams reach 5–12 MB/s
combined. Expect wall-clock download time on the order of 60–90 minutes; it can
be longer at peak times and drop to ~30 minutes on a fast link. The downloader
is idempotent — re-running skips archives that are already on disk — and all
three ZIPs are deleted as they are extracted, so peak transient disk usage is
~23 GB under `--jobs 3` and ~8.7 GB under `--jobs 1`.

## Dataset

The Kuopio Gait Dataset (Lavikainen et al. 2024, *Data in Brief*; Zenodo DOI:
[10.5281/zenodo.10559504](https://doi.org/10.5281/zenodo.10559504)) provides
synchronized IMU accelerometer, Vicon optical motion capture, and floor-embedded
force-plate recordings for 47 usable subjects (17F/30M) walking barefoot at three
instructed speeds on a short overground walkway at the University of Eastern
Finland's HUMEA Laboratory. Anthropometrics are caliper-measured rather than
self-reported. The dataset is distributed under CC-BY 4.0 by the original authors;
this repository does not redistribute the raw files — `bin/download_data.sh` fetches
them directly from Zenodo on setup.

The build pipeline reads the extracted IMU accelerometer files and the Vicon C3D
force-plate channels, runs an independent heel-strike detector on each, converts
both sides to cadence (steps per minute), and writes per-trial cadence error
(`cadence_imu − cadence_plate`) as the modeled outcome. The pelvis IMU is the
primary signal; the same detector is additionally run on the other six body-worn
locations as a sensitivity analysis.

Full column-level documentation of the raw dataset is in
[`data/dataset_info.md`](data/dataset_info.md). The methods, full model
specifications, and every numerical claim are documented in
[`report/wearable_calibration_bayes_report.pdf`](report/wearable_calibration_bayes_report.pdf).

## Results

The four-model audit finds no demographic effect on algorithm error detectable above
the noise in this 47-subject cohort. The female-minus-male cadence-error contrast is
−0.32 spm (Model 3, 95% HDI [−2.03, +1.17]); adjusting additionally for measured leg
length, inter-ASIS distance, and mass widens the residual contrast to −0.65 spm
(Model 4, 95% HDI [−2.64, +1.11]) — a suppression pattern rather than the mediation
pattern the audit chain was pre-registered against. All three anthropometric
coefficients have 95% HDIs that cross zero. Leave-one-out cross-validation at both
trial and subject grains shows Models 2b, 3, and 4 tied within standard error: the
demographic layers add no detectable predictive value on top of the purely structural
Student-t / per-subject-σ baseline. The audit rules out effects larger than roughly
±1.5 spm per SD of body geometry and leaves the door open to smaller effects that a
larger cohort could resolve.

Full methods, diagnostics, model specifications, and limitations are in
[`report/wearable_calibration_bayes_report.pdf`](report/wearable_calibration_bayes_report.pdf).

## References

Works cited above; full bibliography in the
[report PDF](report/wearable_calibration_bayes_report.pdf).

- Criado Perez, C. (2019). *Invisible Women: Data Bias in a World Designed for Men.*
  Abrams Press.
- Crouter, S. E., Schneider, P. L., & Bassett, D. R. Jr. (2005). Spring-levered
  versus piezo-electric pedometer accuracy in overweight and obese adults.
  *Medicine & Science in Sports & Exercise*, 37(10), 1673–1679.
  [doi:10.1249/01.mss.0000181677.36658.a8](https://doi.org/10.1249/01.mss.0000181677.36658.a8)
- Sequeira, M. M., Rickenbach, M., Wietlisbach, V., Tullen, B., & Schutz, Y. (1995).
  Physical activity assessment using a pedometer and its comparison with a
  questionnaire in a large population survey. *American Journal of Epidemiology*,
  142(9), 989–999.
  [doi:10.1093/oxfordjournals.aje.a117748](https://doi.org/10.1093/oxfordjournals.aje.a117748)
- Rowe, D. A., Welk, G. J., Heil, D. P., Mahar, M. T., Kemble, C. D.,
  Calabro, M. A., & Camenisch, K. (2011). Stride rate recommendations for
  moderate-intensity walking. *Medicine & Science in Sports & Exercise*, 43(2),
  312–318.
  [doi:10.1249/MSS.0b013e3181e9d99a](https://doi.org/10.1249/MSS.0b013e3181e9d99a)
- Straczkiewicz, M., Huang, E. J., & Onnela, J.-P. (2023). A "one-size-fits-most"
  walking recognition method for smartphones, smartwatches, and wearable
  accelerometers. *npj Digital Medicine*, 6, 29.
  [doi:10.1038/s41746-022-00745-z](https://doi.org/10.1038/s41746-022-00745-z)
- Lavikainen, J., Vartiainen, P., Stenroth, L., Karjalainen, P. A., Korhonen, R. K.,
  Liukkonen, M. K., & Mononen, M. E. (2024). Kuopio gait dataset: motion capture,
  inertial measurement and video-based sagittal-plane keypoint data from walking
  trials. *Data in Brief*, 56, 110841.
  [doi:10.1016/j.dib.2024.110841](https://doi.org/10.1016/j.dib.2024.110841)

**Software.** Built on PyMC [Abril-Pla et al., 2023] and ArviZ [Martin et al., 2026];
see [`environment.yaml`](environment.yaml) for the full pinned dependency set.

## License

This repository is licensed under [CC BY-NC 4.0](LICENSE) (Creative Commons
Attribution-NonCommercial 4.0 International). You are welcome to clone it, run the
notebooks, read the report, and learn from the methods. Any use of the code, figures,
or writeup must attribute this work; commercial use is not permitted without written
permission. See [`LICENSE`](LICENSE) for the full terms.

The Kuopio Gait Dataset itself is licensed separately under CC BY 4.0 by the original
authors (Lavikainen et al. 2024) and is not redistributed by this repository.

## How to cite

If you reference this work, please cite:

> Griffith, M. (2026). *Wearable Calibration Bayes: A Hierarchical Bayesian Audit of
> Step-Counting Algorithm Bias by Demographics.* Final project for ISyE 6420
> (Bayesian Statistics), Georgia Tech, Spring 2026.
> https://github.com/meeshmg/wearable-calibration-bayes

BibTeX:

```bibtex
@misc{griffith2026wearable,
  author       = {Griffith, Michelle},
  title        = {Wearable Calibration Bayes: A Hierarchical Bayesian Audit of
                  Step-Counting Algorithm Bias by Demographics},
  year         = {2026},
  howpublished = {\url{https://github.com/meeshmg/wearable-calibration-bayes}},
  note         = {Final project for ISyE 6420 (Bayesian Statistics), Georgia Tech,
                  Spring 2026}
}
```

## About the author

Michelle Griffith (she/her) is a machine learning engineer and full-stack data
scientist based in Moab, Utah. She builds and maintains production ML systems in
SaaS environments — currently fraud detection and propensity modeling at
[BambooHR](https://www.bamboohr.com) — and founded [BizziB AI](https://bizzib.ai),
a data-science consultancy. She is motivated by building trustworthy, transparent
technology that improves the human experience, which the fairness framing of this
project reflects directly.

She is pursuing an MS in Computer Science with a Machine Learning specialization at
Georgia Tech.

**Contact.** [michelle@bizzib.ai](mailto:michelle@bizzib.ai) for consultancy and
follow-up work; [mgriffith42@gatech.edu](mailto:mgriffith42@gatech.edu) for
course-related questions. Also on
[LinkedIn](https://www.linkedin.com/in/michellemgriffith/).
