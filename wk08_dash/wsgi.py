from werkzeug.middleware.dispatcher import DispatcherMiddleware

from flask_app import flask_app
from dash_app import app


application = DispatcherMiddleware(flask_app, {
    '/dash': app.server,
})
