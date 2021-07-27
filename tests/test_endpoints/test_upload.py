#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2020      David Straub
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

"""Tests uploading media files POST."""

import hashlib
import random
import shutil
import tempfile
import unittest
from io import BytesIO
from typing import Dict
from unittest.mock import patch

from gramps.cli.clidbman import CLIDbManager
from gramps.gen.dbstate import DbState
from PIL import Image

from gramps_webapi.app import create_app
from gramps_webapi.auth.const import ROLE_GUEST, ROLE_OWNER
from gramps_webapi.const import ENV_CONFIG_FILE, TEST_AUTH_CONFIG


def get_headers(client, user: str, password: str) -> Dict[str, str]:
    """Get the auth headers for a specific user."""
    rv = client.post("/api/token/", json={"username": user, "password": password})
    access_token = rv.json["access_token"]
    return {"Authorization": "Bearer {}".format(access_token)}


def get_image(color):
    """Get a JPEG image."""
    image_file = BytesIO()
    image = Image.new("RGBA", size=(50, 50), color=color)
    image.save(image_file, "png")
    image_file.seek(0)
    return image_file


class TestUpload(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "Test Web API"
        cls.dbman = CLIDbManager(DbState())
        cls.dbman.create_new_db_cli(cls.name, dbid="sqlite")
        with patch.dict("os.environ", {ENV_CONFIG_FILE: TEST_AUTH_CONFIG}):
            cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.media_base_dir = tempfile.mkdtemp()
        cls.app.config["MEDIA_BASE_DIR"] = cls.media_base_dir
        cls.client = cls.app.test_client()
        sqlauth = cls.app.config["AUTH_PROVIDER"]
        sqlauth.create_table()
        sqlauth.add_user(name="user", password="123", role=ROLE_GUEST)
        sqlauth.add_user(name="admin", password="123", role=ROLE_OWNER)

    @classmethod
    def tearDownClass(cls):
        cls.dbman.remove_database(cls.name)
        shutil.rmtree(cls.media_base_dir)

    def test_upload_new_media(self):
        """Add new media object."""
        img = get_image(0)
        img.seek(0)
        checksum = hashlib.md5(img.getbuffer()).hexdigest()
        img.seek(0)
        # try as guest - not allowed
        headers = get_headers(self.client, "user", "123")
        rv = self.client.post(
            "/api/media/", data=None, headers=headers, content_type="image/jpeg"
        )
        self.assertEqual(rv.status_code, 403)
        # try as admin
        headers = get_headers(self.client, "admin", "123")
        rv = self.client.post(
            "/api/media/", data=img.read(), headers=headers, content_type="image/jpeg"
        )
        self.assertEqual(rv.status_code, 201)
        # get the object
        rv = self.client.get("/api/media/", headers=headers)
        self.assertEqual(rv.status_code, 200)
        res = rv.json[0]
        self.assertEqual(res["path"], f"{res['checksum']}.jpg")
        self.assertEqual(res["mime"], "image/jpeg")
        self.assertEqual(res["checksum"], checksum)
