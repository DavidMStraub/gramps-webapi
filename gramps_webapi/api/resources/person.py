"""Person API resource."""

from typing import Dict

from gramps.gen.lib import Person

from .base import (
    GrampsObjectProtectedResource,
    GrampsObjectResourceHelper,
    GrampsObjectsProtectedResource,
)
from .util import (
    get_extended_attributes,
    get_family_by_handle,
    get_person_profile_for_object,
)


class PersonResourceHelper(GrampsObjectResourceHelper):
    """Person resource helper."""

    gramps_class_name = "Person"

    def object_extend(self, obj: Person, args: Dict) -> Person:
        """Extend person attributes as needed."""
        db_handle = self.db_handle
        if args["profile"]:
            obj.profile = get_person_profile_for_object(
                db_handle, obj, with_family=True, with_events=True
            )
        if args["extend"]:
            obj.extended = get_extended_attributes(db_handle, obj)
            obj.extended.update(
                {
                    "families": [
                        get_family_by_handle(db_handle, handle)
                        for handle in obj.family_list
                    ],
                    "parent_families": [
                        get_family_by_handle(db_handle, handle)
                        for handle in obj.parent_family_list
                    ],
                    "primary_parent_family": get_family_by_handle(
                        db_handle, obj.get_main_parents_family_handle()
                    ),
                }
            )
        return obj


class PersonResource(GrampsObjectProtectedResource, PersonResourceHelper):
    """Person resource."""


class PeopleResource(GrampsObjectsProtectedResource, PersonResourceHelper):
    """People resource."""
