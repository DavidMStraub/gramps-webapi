#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2020-2024      David Straub
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

"""Functions for converting Gramps objects to indexable text."""

from datetime import datetime
from typing import Any, Dict, Generator, Optional, Sequence, Tuple

from gramps.gen.db.base import DbReadBase
from gramps.gen.lib import Name, Place
from gramps.gen.lib.primaryobj import BasicPrimaryObject as GrampsObject
from unidecode import unidecode

from ...const import GRAMPS_OBJECT_PLURAL, PRIMARY_GRAMPS_OBJECTS


def object_to_strings(obj) -> Tuple[str, str]:
    """Create strings from a Gramps object's textual pieces.

    This function returns a tuple of two strings: the first one contains
    the concatenated string of the object and the strings of all
    non-private child objects. The second contains the concatenated
    strings of all private child objects."""
    strings = obj.get_text_data_list()
    private_strings = []
    if hasattr(obj, "gramps_id") and obj.gramps_id not in strings:
        # repositories and notes currently don't have gramps_id on their
        # text_data_list, so it is added here explicitly if missing
        strings.append(obj.gramps_id)
    text_data_child_list = obj.get_text_data_child_list()
    if isinstance(obj, Place) and obj.name not in text_data_child_list:
        # fix necessary for Gramps 5.1
        # (see https://github.com/gramps-project/gramps-web-api/issues/245)
        text_data_child_list.append(obj.name)
    for child_obj in text_data_child_list:
        if hasattr(child_obj, "get_text_data_list"):
            if hasattr(child_obj, "private") and child_obj.private:
                private_strings += child_obj.get_text_data_list()
            else:
                strings += child_obj.get_text_data_list()
            if isinstance(child_obj, Name):
                # for names, need to iterate one level deeper to also find surnames
                for grandchild_obj in child_obj.get_text_data_child_list():
                    if hasattr(grandchild_obj, "get_text_data_list"):
                        if hasattr(child_obj, "private") and child_obj.private:
                            private_strings += grandchild_obj.get_text_data_list()
                        else:
                            strings += grandchild_obj.get_text_data_list()
    return process_strings(strings), process_strings(private_strings)


def process_strings(strings: Sequence[str]) -> str:
    """Process a list of strings to a joined string.

    Removes duplicates and adds transliterated strings for strings containing
    unicode characters.
    """

    def generator():
        all_strings = set()
        for string in strings:
            if string not in all_strings:
                all_strings.add(string)
                yield string
                decoded_string = unidecode(string)
                if decoded_string != string and decoded_string not in all_strings:
                    all_strings.add(decoded_string)
                    yield decoded_string

    return " ".join(generator())


def obj_strings_from_handle(
    db_handle: DbReadBase, class_name: str, handle
) -> Optional[Dict[str, Any]]:
    """Return object strings from a handle and Gramps class name."""
    query_method = db_handle.method("get_%s_from_handle", class_name)
    obj = query_method(handle)
    return obj_strings_from_object(db_handle=db_handle, class_name=class_name, obj=obj)


def obj_strings_from_object(
    db_handle: DbReadBase, class_name: str, obj: GrampsObject
) -> Optional[Dict[str, Any]]:
    """Return object strings from a handle and Gramps class name."""
    obj_string, obj_string_private = object_to_strings(obj)
    private = hasattr(obj, "private") and obj.private
    if obj_string:
        return {
            "class_name": class_name,
            "handle": obj.handle,
            "private": private,
            "string": obj_string,
            "string_private": obj_string_private,
            "change": datetime.fromtimestamp(obj.change),
        }
    return None


def iter_obj_strings(
    db_handle: DbReadBase,
) -> Generator[Dict[str, Any], None, None]:
    """Iterate over object strings in the whole database."""
    for class_name in PRIMARY_GRAMPS_OBJECTS:
        plural_name = GRAMPS_OBJECT_PLURAL[class_name]
        iter_method = db_handle.method("iter_%s", plural_name)
        for obj in iter_method():
            obj_strings = obj_strings_from_object(db_handle, class_name, obj)
            if obj_strings:
                yield obj_strings


def get_object_timestamps(db_handle: DbReadBase):
    """Get a dictionary with change timestamps of all objects in the DB."""
    d = {}
    for class_name in PRIMARY_GRAMPS_OBJECTS:
        d[class_name] = set()
        iter_method = db_handle.method("iter_%s_handles", class_name)
        for handle in iter_method():
            query_method = db_handle.method("get_%s_from_handle", class_name)
            obj = query_method(handle)
            d[class_name].add((handle, datetime.fromtimestamp(obj.change)))
    return d
