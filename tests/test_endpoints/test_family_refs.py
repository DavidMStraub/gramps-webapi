#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2026      David Straub
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

"""Tests for family objects referencing people that do not exist."""

import os
import unittest
import uuid
from typing import Dict
from unittest.mock import patch

from gramps.cli.clidbman import CLIDbManager
from gramps.gen.dbstate import DbState

from gramps_webapi.app import create_app
from gramps_webapi.auth import add_user, user_db
from gramps_webapi.auth.const import ROLE_EDITOR
from gramps_webapi.const import ENV_CONFIG_FILE, TEST_AUTH_CONFIG


def get_headers(client, user: str, password: str) -> Dict[str, str]:
    """Get the auth headers for a specific user."""
    rv = client.post("/api/token/", json={"username": user, "password": password})
    access_token = rv.json["access_token"]
    return {"Authorization": "Bearer {}".format(access_token)}


def make_handle() -> str:
    """Make a new valid handle."""
    return str(uuid.uuid4())


class TestFamilyBrokenReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "Test Web API"
        cls.dbman = CLIDbManager(DbState())
        dbpath, _ = cls.dbman.create_new_db_cli(cls.name, dbid="sqlite")
        tree = os.path.basename(dbpath)
        with patch.dict("os.environ", {ENV_CONFIG_FILE: TEST_AUTH_CONFIG}):
            cls.app = create_app(config_from_env=False)
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            user_db.create_all()
            add_user(name="editor", password="123", role=ROLE_EDITOR, tree=tree)
        cls.headers = get_headers(cls.client, "editor", "123")

    @classmethod
    def tearDownClass(cls):
        cls.dbman.remove_database(cls.name)

    def add_person(self) -> str:
        """Add a person and return its handle."""
        handle = make_handle()
        rv = self.client.post(
            "/api/people/",
            json={"_class": "Person", "handle": handle},
            headers=self.headers,
        )
        self.assertEqual(rv.status_code, 201)
        return handle

    def add_family(self, **kwargs) -> str:
        """Add a family and return its handle."""
        handle = make_handle()
        rv = self.client.post(
            "/api/families/",
            json={"_class": "Family", "handle": handle, **kwargs},
            headers=self.headers,
        )
        self.assertEqual(rv.status_code, 201)
        return handle

    def delete_person_raw(self, handle: str) -> None:
        """Delete a person without cleaning up references to it.

        This is what a raw transaction (e.g. an undo) does, and is how families
        with broken parent or child references come about.
        """
        rv = self.client.get(f"/api/people/{handle}", headers=self.headers)
        self.assertEqual(rv.status_code, 200)
        trans = [
            {
                "type": "delete",
                "_class": "Person",
                "handle": handle,
                "old": rv.json,
                "new": None,
            }
        ]
        rv = self.client.post(
            "/api/transactions/?background=1&force=1", json=trans, headers=self.headers
        )
        self.assertEqual(rv.status_code, 200)
        rv = self.client.get(f"/api/people/{handle}", headers=self.headers)
        self.assertEqual(rv.status_code, 404)

    def test_add_family_missing_parent(self):
        """Adding a family with a nonexistent father is rejected."""
        handle_family = make_handle()
        handle_missing = make_handle()
        rv = self.client.post(
            "/api/families/",
            json={
                "_class": "Family",
                "handle": handle_family,
                "father_handle": handle_missing,
            },
            headers=self.headers,
        )
        self.assertEqual(rv.status_code, 422)
        self.assertIn(handle_missing, rv.json["error"]["message"])
        # the family must not have been created
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.status_code, 404)

    def test_add_family_missing_child(self):
        """Adding a family with a nonexistent child is rejected."""
        handle_family = make_handle()
        handle_missing = make_handle()
        rv = self.client.post(
            "/api/families/",
            json={
                "_class": "Family",
                "handle": handle_family,
                "child_ref_list": [{"_class": "ChildRef", "ref": handle_missing}],
            },
            headers=self.headers,
        )
        self.assertEqual(rv.status_code, 422)
        self.assertIn(handle_missing, rv.json["error"]["message"])
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.status_code, 404)

    def test_update_family_missing_parent(self):
        """Setting a nonexistent person as father is rejected, not a 500."""
        handle_mother = self.add_person()
        handle_family = self.add_family(mother_handle=handle_mother)
        handle_missing = make_handle()
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        family = rv.json
        family["father_handle"] = handle_missing
        rv = self.client.put(
            f"/api/families/{handle_family}", json=family, headers=self.headers
        )
        self.assertEqual(rv.status_code, 422)
        self.assertIn(handle_missing, rv.json["error"]["message"])
        # the update must have been rolled back completely
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.json["father_handle"], "")

    def test_update_family_missing_child(self):
        """Adding a nonexistent person as child is rejected, not a 500."""
        handle_mother = self.add_person()
        handle_family = self.add_family(mother_handle=handle_mother)
        handle_missing = make_handle()
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        family = rv.json
        family["child_ref_list"] = [{"_class": "ChildRef", "ref": handle_missing}]
        rv = self.client.put(
            f"/api/families/{handle_family}", json=family, headers=self.headers
        )
        self.assertEqual(rv.status_code, 422)
        self.assertIn(handle_missing, rv.json["error"]["message"])
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.json["child_ref_list"], [])

    def test_update_family_remove_broken_parent(self):
        """A family with a broken father reference can be repaired."""
        handle_father = self.add_person()
        handle_mother = self.add_person()
        handle_family = self.add_family(
            father_handle=handle_father, mother_handle=handle_mother
        )
        self.delete_person_raw(handle_father)
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        family = rv.json
        self.assertEqual(family["father_handle"], handle_father)
        family["father_handle"] = ""
        rv = self.client.put(
            f"/api/families/{handle_family}", json=family, headers=self.headers
        )
        self.assertEqual(rv.status_code, 200)
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.json["father_handle"], "")
        self.assertEqual(rv.json["mother_handle"], handle_mother)

    def test_update_family_remove_broken_child(self):
        """A family with a broken child reference can be repaired."""
        handle_child = self.add_person()
        handle_mother = self.add_person()
        handle_family = self.add_family(
            mother_handle=handle_mother,
            child_ref_list=[{"_class": "ChildRef", "ref": handle_child}],
        )
        self.delete_person_raw(handle_child)
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        family = rv.json
        family["child_ref_list"] = []
        rv = self.client.put(
            f"/api/families/{handle_family}", json=family, headers=self.headers
        )
        self.assertEqual(rv.status_code, 200)
        rv = self.client.get(f"/api/families/{handle_family}", headers=self.headers)
        self.assertEqual(rv.json["child_ref_list"], [])
