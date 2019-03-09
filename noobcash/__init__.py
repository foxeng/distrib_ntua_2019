from flask import Flask

app = Flask(__name__)
# TODO: Set proper defaults
app.config.from_mapping(
    NOOBCASH_DIFFICULTY=1,
    NOOBCASH_CAPACITY=1
)
app.config.from_pyfile('config.py', silent=False)
app.config.from_envvar('NOOBCASH_SETTINGS', silent=True)
import noobcash.app
