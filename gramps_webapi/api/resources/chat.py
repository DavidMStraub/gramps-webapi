#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2024      David Straub
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

"""AI chat endpoint."""

from marshmallow import Schema
from webargs import fields

from ..llm import answer_prompt_retrieve
from ..util import get_tree_from_jwt, use_args, abort_with_message
from . import ProtectedResource
from ...auth.const import PERM_VIEW_PRIVATE
from ..auth import has_permissions


class ChatMessageSchema(Schema):
    role = fields.Str(required=True)
    message = fields.Str(required=True)


class ChatResource(ProtectedResource):
    """AI chat resource."""

    @use_args(
        {
            "query": fields.Str(required=True),
            "history": fields.List(fields.Nested(ChatMessageSchema), required=False),
        },
        location="json",
    )
    def post(self, args):
        """Create a chat response."""
        tree = get_tree_from_jwt()
        try:
            response = answer_prompt_retrieve(
                prompt=args["query"],
                tree=tree,
                include_private=has_permissions({PERM_VIEW_PRIVATE}),
                history=args.get("history"),
            )
        except ValueError:
            raise
            abort_with_message(422, "Invalid message format")
        return {"response": response}