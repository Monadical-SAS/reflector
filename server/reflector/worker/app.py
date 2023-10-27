from celery import Celery
from reflector.settings import settings

app = Celery(__name__)
app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.autodiscover_tasks(
    [
        "reflector.pipelines.main_live_pipeline",
    ]
)
