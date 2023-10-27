from celery import Celery
from reflector.settings import settings

app = Celery(__name__)
app.conf.broker_url = settings.CELERY_BROKER_URL
app.conf.result_backend = settings.CELERY_RESULT_BACKEND
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks(
    [
        "reflector.pipelines.main_live_pipeline",
    ]
)
