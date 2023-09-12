def metrics_init(app, instrumentator):
    instrumentator.instrument(app)
    instrumentator.expose(app)
