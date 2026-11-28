from .settings import *

DATABASES = {
    "default": {
        **DATABASES["default"],
        "TEST": {
            "NAME": "/data/test_concurrence.sqlite3",
        },
    },
}
