# Kuopio Gait Dataset

> **Source.** This document is the dataset description copied verbatim from the
> Zenodo record landing page ([10.5281/zenodo.10559504](https://doi.org/10.5281/zenodo.10559504))
> and reformatted for readability. It is included in this repository as a richer
> reference than the brief `readme.txt` that ships with the archive download.
> Original content is © the dataset authors and is reproduced here under the
> dataset's CC BY 4.0 license (see [License](#license) below).

**Title.** Kuopio gait dataset: motion capture, inertial measurement and
video-based sagittal-plane keypoint data from walking trials

**Published.** January 24, 2024 — Version 1.0.0
**Type.** Dataset (Open Access)
**DOI.** [10.5281/zenodo.10559504](https://doi.org/10.5281/zenodo.10559504)

## Authors / Creators

- **Lavikainen, Jere** (Contact person) — University of Eastern Finland;
  Wellbeing services county of North Savo
- **Vartiainen, Paavo** (Supervisor) — University of Eastern Finland
- **Stenroth, Lauri** (Supervisor) — University of Eastern Finland
- **Karjalainen, Pasi** (Supervisor) — University of Eastern Finland
- **Korhonen, Rami** (Supervisor) — University of Eastern Finland
- **Liukkonen, Mimmi** (Researcher) — Kuopio University Hospital;
  Wellbeing services county of North Savo
- **Mononen, Mika** (Supervisor) — University of Eastern Finland

## Description

This dataset contains motion capture (3D marker trajectories, ground reaction
forces and moments), inertial measurement unit (wearable Movella Xsens MTw
Awinda sensors on the pelvis, both thighs, both shanks, and both feet), and
sagittal-plane video (anatomical keypoints identified with the OpenPose human
pose estimation algorithm) data.

The data is from 51 willing participants and collected in the HUMEA laboratory
in the University of Eastern Finland, Kuopio, Finland, between 2022 and 2023.
All trials were conducted barefoot.

The file structure contains an Excel file containing information of the
participants, data folders under each subject (numbered 01 to 51), and a
MATLAB script.

## Participant Information (Excel file)

The Excel file has the following data for the participants:

| Column label | Description |
| --- | --- |
| `ID` | identifier of the participant from 1 to 51 |
| `Age` | age of the participant in years |
| `Gender` | biological sex (M = male, F = female) |
| `Leg` | the participant's dominant leg, identified by asking which foot the participant would use to kick a football (R = right, L = left) |
| `Height` | height of the participant in centimeters |
| `Invalid_trials` | list of invalid trials in the motion capture data, usually classified as such because the participant did not properly step on the middle force plate |
| `IAD` | inter-asis distance in millimeters; measured with a caliper from left to right anterior superior iliac spine |
| `Left_knee_width` | width of the left knee in millimeters; measured with a caliper from medial epicondyle to lateral epicondyle |
| `Right_knee_width` | same as above for the right knee |
| `Left_ankle_width` | width of the left ankle in millimeters; measured with a caliper from medial malleolus to lateral malleolus |
| `Right_ankle_width` | same as above for the right ankle |
| `Left_thigh_length` | length of the left leg in millimeters; measured with a measuring tape from the greater trochanter of the left femur to the lateral epicondyle of the left femur |
| `Right_thigh_length` | same as above for the right thigh |
| `Left_shank_length` | length of the left shank in millimeters; measured with a measuring tape from the medial epicondyle of the femur to the medial malleolus of the tibia |
| `Right_shank_length` | same as above for the right shank |
| `Mass` | the participant's mass in kilograms; measured on a force plate just before the walking measurements |
| `ICD` | inter-condylar distance of the knee of the dominant leg in millimeters; measured from low-field MRI |
| `Left_knee_width_mocap` | distance between reflective motion capture markers on the medial and lateral epicondyles of the knee in millimeters; measured from a static standing trial; a value of −1 means the data is missing because the participant did not have those markers |
| `Right_knee_width_mocap` | same as above for the right knee |

## Per-Subject Folder Layout

The folders under each subject (folders numbered 01 to 51) are as follows:

### `imu/`

"Raw" inertial measurement unit (IMU) data files that can be read with Xsens
Device API (included in Xsens MT Manager 4.6, which may be unavailable these
days, not sure). You won't need this if you use the data in the
`imu_extracted` folder.

### `imu_extracted/`

IMU data extracted from those data files using the Xsens Device API, so you
don't have to.

The data is saved as MATLAB structs where the fields are named as a sensor ID
(e.g., `B42D48`). The sensor IDs and their corresponding IMU locations are as
follows:

| IMU location | Sensor ID |
| --- | --- |
| Pelvis IMU | `B42DA3` |
| Right femur IMU | `B42DA2` |
| Left femur IMU | `B42D4D` |
| Right tibia IMU | `B42DAE` |
| Left tibia IMU | `B42D53` |
| Right foot IMU | `B42D48` |
| Left foot IMU | `B42D51` (except for subjects 01 and 02, where left foot IMU has the ID `B42D4E`) |

Some of the data are just zeros as they couldn't be read from these sensors,
but under each sensor, the fields `calibratedAcceleration`, `freeAcceleration`,
`time`, `rotationMatrix`, and `quaternion` contain usable data.

- **`time`** — Contains time stamps of the measurement at each frame recorded
  at 100 Hz, so if you remove the first value from all values in the `time`
  vector and divide the result by 100, you will get the time in seconds from
  the beginning of the walking trial.
- **`calibratedAcceleration` and `freeAcceleration`** — Contain triaxial
  acceleration data from the accelerometers of the IMU. `freeAcceleration` is
  just `calibratedAcceleration` without the effect of Earth's gravitational
  acceleration.
- **`rotationMatrix`** — Orientations of the IMU as rotation matrices.
- **`quaternion`** — Orientations of the IMU as quaternions.

### `openpose/`

Trajectories of the keypoints identified from sagittal plane video frames,
saved as JSON files.

- The keypoints are from the BODY_25 model of OpenPose
  (<https://cmu-perceptual-computing-lab.github.io/openpose/web/html/doc/md_doc_02_output.html>).
- Each frame in the video has its own JSON file.
- You can use the function in the script `OpenPose_to_keypoint_table.m` in the
  root folder to read the keypoint trajectories and confidences of all frames
  in a walking trial into MATLAB tables. The function takes as argument the
  path to the folder containing the JSON files of the walking trial.

### `mocap/`

Motion capture data (marker trajectories and force plate recordings) in C3D
and Vicon Nexus compatible formats.

---

Note that some subjects (11, 14, 37, 49) do not have keypoint and IMU data.
The folders under each subject are divided into three ZIP archives with 17
subjects each.

The script `OpenPose_to_keypoint_table.m` is a MATLAB script for extracting
keypoint trajectories and confidences from JSON files into tables in MATLAB.

## Motion Capture Markers

The marker trajectories of the motion capture data include the following
markers (see notes below the table):

| Marker name | Location |
| --- | --- |
| `Torso1` | manubrium of the sternum |
| `Torso2` | acromion of the right shoulder |
| `Torso3` | acromion of the left shoulder |
| `Torso4` | 7th cervical vertebra |
| `Pelvis1` to `Pelvis4` | rigid cluster strapped behind the pelvis |
| `RFemur1` to `RFemur4` | rigid cluster strapped laterally to the right thigh |
| `RFemur5` | medial epicondyle of the knee of the right leg |
| `RFemur6` | lateral epicondyle of the knee of the right leg |
| `RTibia1` to `RTibia4` | rigid cluster strapped laterally to the right shank |
| `RTibia5` | medial malleolus of the right ankle |
| `RTibia6` | lateral malleolus of the right ankle |
| `RFoot1` | behind the heel |
| `RFoot2` | 1st distal phalanx |
| `RFoot3` | 4th proximal phalanx |
| `RFoot4` | proximally / posteriorly on IMU on the metatarsals |
| `RFoot5` | distally / anteriorly on IMU on the metatarsals |

**Notes:**

- In the table above, only right leg markers are described; the left leg
  markers start with `L` instead of `R` and were placed symmetrically.
- During walking trials, medial knee markers (`RFemur5` and `LFemur5`) were
  removed if they physically collided.
- Participant 1 wore an incomplete marker set.
- Participant 2 only had torso markers on the manubrium of the sternum and on
  the 7th cervical vertebra.
- The pelvis and thigh clusters were 3D printed, which allowed placing an IMU
  on the cluster and placing markers rigidly several centimeters away from the
  skin surface (see figure 6.5 of [this dissertation](https://erepo.uef.fi/items/0397f5b1-36f5-4c52-ac1c-cf68a1ad3906)).
- In some participants, the `Torso4` marker was on the acromion of the left
  shoulder and the `Torso3` marker on the 7th cervical vertebra, instead of
  the other way around.
- In some participants, the second foot marker (e.g., `RFoot2`) was on the
  4th proximal phalanx and the third foot marker (e.g., `RFoot3`) was on the
  1st distal phalanx instead of the other way around.
- Automatic marker labeling may have misplaced other markers in some of the
  trials, so manual verification is recommended.

## Related Publications

- **Data descriptor.** Publication in *Data in Brief*:
  <https://doi.org/10.1016/j.dib.2024.110841>
- This data was also used in [this paper](http://urn.fi/URN:ISBN:978-952-61-5276-9)
  and described in section 6.3 of
  [this dissertation](https://link.springer.com/article/10.1007/s10439-024-03594-x).

## Contact

Jere Lavikainen — <jere.lavikainen@uef.fi>

## Funding and Ethics (Notes, English)

The collection of this dataset involved research projects that received funding
from the Research Council of Finland (grants 324994, 328920, 352666, 332915,
322423, 349469 and 334773 — under the frame of ERA PerMed), the Research
Committee of the Kuopio University Hospital Catchment Area for the State
Research Funding (grant 5654242), and the Sigrid Juselius Foundation
(grants 230123, 230093).

The collection of this dataset was reviewed and approved by the University of
Eastern Finland Committee on Research Ethics (statement no. 16/2022).

## License

The Kuopio Gait Dataset is distributed by the original authors under the
**Creative Commons Attribution 4.0 International (CC BY 4.0)** license. This
documentation page, reproduced verbatim from the Zenodo record, is included
here under the same license. This repository does not redistribute the raw
dataset; `bin/download_data.sh` fetches it directly from Zenodo on setup.
Users must comply with the dataset's own license in addition to the terms in
this repository's `LICENSE` file.

## How to Cite the Dataset

> Lavikainen, J., Vartiainen, P., Stenroth, L., Karjalainen, P. A.,
> Korhonen, R. K., Liukkonen, M. K., & Mononen, M. E. (2024). *Kuopio gait
> dataset: motion capture, inertial measurement and video-based sagittal-plane
> keypoint data from walking trials.* Zenodo.
> <https://doi.org/10.5281/zenodo.10559504>

Companion data descriptor:

> Lavikainen, J., Vartiainen, P., Stenroth, L., Karjalainen, P. A.,
> Korhonen, R. K., Liukkonen, M. K., & Mononen, M. E. (2024). Kuopio gait
> dataset: motion capture, inertial measurement and video-based sagittal-plane
> keypoint data from walking trials. *Data in Brief*, 56, 110841.
> <https://doi.org/10.1016/j.dib.2024.110841>
