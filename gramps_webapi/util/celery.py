"""Utility functions for celery."""

from celery import Task
from celery import current_app as current_celery_app


def make_celery(app):
    """App factory for celery."""
    celery = current_celery_app
    celery.conf.update(app.config["CELERY_CONFIG"])

    class ContextTask(Task):
        """Celery task which is aware of the flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
