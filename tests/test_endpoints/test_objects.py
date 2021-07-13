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

"""Tests for the object creation endpoint."""

import unittest
import uuid
from typing import Dict
from unittest.mock import patch

from gramps.cli.clidbman import CLIDbManager
from gramps.gen.dbstate import DbState

from gramps_webapi.app import create_app
from gramps_webapi.auth.const import ROLE_GUEST, ROLE_OWNER
from gramps_webapi.const import ENV_CONFIG_FILE, TEST_AUTH_CONFIG


def get_headers(client, user: str, password: str) -> Dict[str, str]:
    """Get the auth headers for a specific user."""
    rv = client.post("/api/token/", json={"username": user, "password": password})
    access_token = rv.json["access_token"]
    return {"Authorization": "Bearer {}".format(access_token)}


def make_handle() -> str:
    """Make a new valid handle."""
    return str(uuid.uuid4())


class TestObjectEndpoint(unittest.TestCase):
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
        sqlauth.add_user(name="admin", password="123", role=ROLE_OWNER)

    @classmethod
    def tearDownClass(cls):
        cls.dbman.remove_database(cls.name)

    def test_add_note(self):
        """Add a single note."""
        handle = make_handle()
        obj = [
            {
                "_class": "Note",
                "handle": handle,
                "text": {"_class": "StyledText", "string": "My first note."},
            }
        ]
        headers = get_headers(self.client, "user", "123")
        rv = self.client.post("/api/objects/", json=obj, headers=headers)
        self.assertEqual(rv.status_code, 403)
        headers = get_headers(self.client, "admin", "123")
        rv = self.client.post("/api/objects/", json=obj, headers=headers)
        self.assertEqual(rv.status_code, 201)
        rv = self.client.get(f"/api/notes/{handle}", headers=headers)
        self.assertEqual(rv.status_code, 200)

    def test_add_person(self):
        """Add a person with a birth event."""
        handle_person = make_handle()
        handle_birth = make_handle()
        person = {
            "_class": "Person",
            "handle": handle_person,
            "primary_name": {
                "_class": "Name",
                "surname_list": [{"_class": "Surname", "surname": "Doe",}],
                "first_name": "John",
            },
            "event_ref_list": [
                {
                    "_class": "EventRef",
                    "ref": handle_birth,
                    "role": {"_class": "EventRoleType", "string": "Primary"},
                },
            ],
            "birth_ref_index": 0,
            "gender": 1,
        }
        birth = {
            "_class": "Event",
            "handle": handle_birth,
            "date": {"_class": "Date", "dateval": [2, 10, 1764, False],},
            "type": {"_class": "EventType", "string": "Birth"},
        }
        objects = [person, birth]
        headers = get_headers(self.client, "admin", "123")
        rv = self.client.post("/api/objects/", json=objects, headers=headers)
        self.assertEqual(rv.status_code, 201)
        rv = self.client.get(
            f"/api/people/{handle_person}?extend=event_ref_list", headers=headers
        )
        self.assertEqual(rv.status_code, 200)
        person_dict = rv.json
        self.assertEqual(person_dict["handle"], handle_person)
        self.assertEqual(person_dict["primary_name"]["first_name"], "John")
        self.assertEqual(
            person_dict["primary_name"]["surname_list"][0]["surname"], "Doe"
        )
        self.assertEqual(person_dict["extended"]["events"][0]["handle"], handle_birth)
        self.assertEqual(
            person_dict["extended"]["events"][0]["date"]["dateval"],
            [2, 10, 1764, False],
        )

