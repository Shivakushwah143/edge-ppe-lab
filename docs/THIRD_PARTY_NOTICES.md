# Third-Party Notices

EdgePPE Lab depends on third-party software and an external dataset. This file is informational and is not legal advice; review the upstream license terms before redistributing artifacts.

The training source is the Ultralytics Construction-PPE dataset documented at `https://docs.ultralytics.com/datasets/detect/construction-ppe/`. Ultralytics documents that dataset as AGPL-3.0 and provides the official download through its dataset YAML. The repository does not redistribute the dataset archive; `scripts/prepare_dataset.py` downloads it from the upstream source when the user runs the lab.

Ultralytics YOLO and the other Python packages are installed from their upstream package distributions under their respective licenses. The project intentionally does not vendor those dependencies into the release ZIP.
