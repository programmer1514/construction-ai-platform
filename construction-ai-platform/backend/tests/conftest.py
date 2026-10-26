import io
import os
import sys
from pathlib import Path

os.environ["DEMO_MODE"] = "1"  # tests never call the real API
os.environ["ANTHROPIC_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def make_image(size=(320, 240), fmt="JPEG", color=(120, 110, 100)) -> bytes:
    import random

    img = Image.new("RGB", size, color)
    px = img.load()
    random.seed(1)
    for _ in range(size[0] * size[1] // 8):  # add noise so the file isn't trivially tiny
        px[random.randrange(size[0]), random.randrange(size[1])] = (random.randrange(256),) * 3
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture()
def jpg():
    return make_image()
