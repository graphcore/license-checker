# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

import sys
import logging


def setup_logging():
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
