#
# Gramps Web API - A RESTful API for the Gramps genealogy program
#
# Copyright (C) 2023    David Straub
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

"""Endpoint for importing a media archive."""

import os
import uuid
import zipfile

from flask import Response, current_app, jsonify, request

from ...auth.const import PERM_IMPORT_FILE
from ..auth import require_permissions
from ..tasks import AsyncResult, import_media_archive, make_task_response, run_task
from ..util import abort_with_message, get_tree_from_jwt
from . import ProtectedResource


class MediaUploadZipResource(ProtectedResource):
    """Resource for uploading an archive of media files."""

    def post(self) -> Response:
        """Upload an archive of media files."""
        require_permissions([PERM_IMPORT_FILE])
        request_stream = request.stream

        # we use EXPORT_DIR as location to store the temporary file
        export_path = current_app.config["EXPORT_DIR"]
        os.makedirs(export_path, exist_ok=True)
        file_name = f"{uuid.uuid4()}.zip"
        file_path = os.path.join(export_path, file_name)

        with open(file_path, "w+b") as ftmp:
            ftmp.write(request_stream.read())

        if os.path.getsize(file_path) == 0:
            abort_with_message(400, "Imported file is empty")

        try:
            with zipfile.ZipFile(file_path) as zip_file:
                zip_file.namelist()
        except zipfile.BadZipFile:
            abort_with_message(400, "The uploaded file is not a valid ZIP file.")

        tree = get_tree_from_jwt()
        task = run_task(
            import_media_archive,
            tree=tree,
            file_name=file_path,
            delete=True,
        )
        if isinstance(task, AsyncResult):
            return make_task_response(task)
        return jsonify(task), 201
