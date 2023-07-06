# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import pytest
from pathlib import Path
from gc_licensing.config import configs


@pytest.fixture
def load_config():
    app_config_path = Path(__file__).parent / "assets" / "config.yml"
    user_config_path = Path(__file__).parent / "assets" / "user.config.yml"
    configs.load(app_config_path, user_config_path)

    return configs
