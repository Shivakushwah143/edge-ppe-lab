from pathlib import Path
import yaml


def test_dataset_yaml_has_canonical_classes():
    cfg = yaml.safe_load(Path('data/ppe.yaml').read_text())
    assert cfg['names'] == {0: 'Person', 1: 'Hardhat', 2: 'NO-Hardhat'}
