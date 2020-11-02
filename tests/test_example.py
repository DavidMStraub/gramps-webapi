"""Tests the example DB."""

import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from gramps.gen.utils.resourcepath import ResourcePath

from gramps_webapi.app import create_app
from gramps_webapi.const import ENV_CONFIG_FILE, TEST_EXAMPLE_CONFIG

from . import ExampleDbInMemory


class TestExampleDb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        env = os.environ.copy()
        env["GRAMPSHOME"] = cls.tmpdir
        _resources = ResourcePath()
        doc_dir = _resources.doc_dir
        ex_file = ExampleDbInMemory().path  # this is an ugly hack! need to tidy up
        subprocess.run(
            ["gramps", "-C", "example", "-i", ex_file, "-q"], env=env, check=True
        )
        with patch.dict(
            "os.environ",
            {ENV_CONFIG_FILE: TEST_EXAMPLE_CONFIG, "GRAMPSHOME": "/tmp/grampshome"},
        ):
            app = create_app()
            app.config["TESTING"] = True
            cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir)

    def test_people(self):
        """Silly test just to get started."""
        rv = self.client.get("/api/people/")
        assert rv.status_code == 200
