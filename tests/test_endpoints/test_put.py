#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2021      David Straub
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

"""Tests updating objects."""

import unittest
import uuid
from typing import Dict
from unittest.mock import patch
from copy import deepcopy

from gramps.cli.clidbman import CLIDbManager
from gramps.gen.dbstate import DbState

from gramps_webapi.app import create_app
from gramps_webapi.auth.const import ROLE_CONTRIBUTOR, ROLE_GUEST, ROLE_OWNER
from gramps_webapi.const import ENV_CONFIG_FILE, TEST_AUTH_CONFIG


def get_headers(client, user: str, password: str) -> Dict[str, str]:
    """Get the auth headers for a specific user."""
    rv = client.post("/api/token/", json={"username": user, "password": password})
    access_token = rv.json["access_token"]
    return {"Authorization": "Bearer {}".format(access_token)}


def make_handle() -> str:
    """Make a new valid handle."""
    return str(uuid.uuid4())


class TestObjectUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "Test Web API"
        cls.dbman = CLIDbManager(DbState())
        cls.dbman.create_new_db_cli(cls.name, dbid="sqlite")
        with patch.dict("os.environ", {ENV_CONFIG_FILE: TEST_AUTH_CONFIG}):
            cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        sqlauth = cls.app.config["AUTH_PROVIDER"]
        sqlauth.create_table()
        sqlauth.add_user(name="user", password="123", role=ROLE_GUEST)
        sqlauth.add_user(name="contributor", password="123", role=ROLE_CONTRIBUTOR)
        sqlauth.add_user(name="admin", password="123", role=ROLE_OWNER)

    @classmethod
    def tearDownClass(cls):
        cls.dbman.remove_database(cls.name)

    def test_update_permission(self):
        """Test update permissions."""
        handle = make_handle()
        obj = {
            "handle": handle,
            "_class": "Note",
            "text": {"_class": "StyledText", "string": "My first note."},
        }
        obj_new = deepcopy(obj)
        obj_new["text"]["string"] = "My second note."
        obj_newer = deepcopy(obj)
        obj_newer["text"]["string"] = "My third note."
        headers_guest = get_headers(self.client, "user", "123")
        headers_contributor = get_headers(self.client, "contributor", "123")
        headers_admin = get_headers(self.client, "admin", "123")
        # create object as contributor
        rv = self.client.post(f"/api/notes/", json=obj, headers=headers_contributor)
        self.assertEqual(rv.status_code, 201)
        # try updating as guest
        rv = self.client.put(
            f"/api/notes/{handle}", json=obj_new, headers=headers_guest
        )
        self.assertEqual(rv.status_code, 403)
        # check it's still unchanged
        rv = self.client.get(f"/api/notes/{handle}", headers=headers_guest)
        self.assertEqual(rv.json["text"]["string"], "My first note.")
        # try updating as contributor
        rv = self.client.put(
            f"/api/notes/{handle}", json=obj_new, headers=headers_contributor
        )
        self.assertEqual(rv.status_code, 403)
        # check it's still unchanged
        rv = self.client.get(f"/api/notes/{handle}", headers=headers_guest)
        etag = rv.headers["ETag"]
        self.assertEqual(rv.status_code, 200)
        # try updating as admin
        rv = self.client.put(
            f"/api/notes/{handle}",
            json=obj_new,
            headers={**headers_admin, "If-Match": etag},
        )
        self.assertEqual(rv.status_code, 200)
        # check it has changed
        rv = self.client.get(f"/api/notes/{handle}", headers=headers_guest)
        self.assertEqual(rv.json["text"]["string"], "My second note.")
        # try again with old ETag
        rv = self.client.put(
            f"/api/notes/{handle}",
            json=obj_newer,
            headers={**headers_admin, "If-Match": etag},
        )
        self.assertEqual(rv.status_code, 412)

    def test_update_transaction(self):
        """Test the update transaction return value."""
        handle = make_handle()
        obj = {
            "handle": handle,
            "_class": "Note",
            "text": {"_class": "StyledText", "string": "Original note."},
        }
        obj_new = deepcopy(obj)
        obj_new["text"]["string"] = "Updated note."
        headers_admin = get_headers(self.client, "admin", "123")
        # create object
        rv = self.client.post(f"/api/notes/", json=obj, headers=headers_admin)
        self.assertEqual(rv.status_code, 201)
        rv = self.client.put(
            f"/api/notes/{handle}", json=obj_new, headers=headers_admin
        )
        self.assertEqual(rv.status_code, 200)
        # check return value
        out = rv.json
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["_class"], "Note")
        self.assertEqual(out[0]["handle"], handle)
        self.assertEqual(out[0]["old"]["text"]["string"], "Original note.")
        self.assertEqual(out[0]["new"]["text"]["string"], "Updated note.")
        self.assertEqual(out[0]["type"], "update")
