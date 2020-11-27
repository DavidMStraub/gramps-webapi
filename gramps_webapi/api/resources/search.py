"""Full-text search endpoint."""

from flask import abort, current_app, jsonify
from webargs import fields
from webargs.flaskparser import use_args

from . import ProtectedResource


class SearchResource(ProtectedResource):
    """Fulltext search resource."""

    @use_args({"q": fields.Str(required=True)}, location="query")
    def get(self, args):
        """Get search result."""
        if not args["q"]:
            abort(400)
        result = current_app.config["SEARCH_INDEXER"].search(args["q"])
        return jsonify(result)