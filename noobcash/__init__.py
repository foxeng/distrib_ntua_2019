from flask import Flask

app = Flask(__name__, instance_relative_config=True) #, instance_path='../instance/')
# TODO: Set proper defaults
app.config.from_mapping(
    #NOOBCASH_DIFFICULTY=1,
    #NOOBCASH_CAPACITY=1
)
app.config.from_envvar('NOOBCASH_SETTINGS', silent=True)

import noobcash.listener.listener
