import os

import pytest

from returnpath.isolation import install

os.environ["RP_ENV_FILE"] = "/dev/null"
os.environ["RP_MODE"] = "local"
os.environ["RP_ALLOW_CONNECTED_WRITES"] = "false"
install()


@pytest.fixture
def world(tmp_path):
    from returnpath.fake import Fake
    from returnpath.storage import connect
    db = connect(tmp_path / "app.sqlite")
    with db:
        db.execute("INSERT INTO cases(id,order_ref,customer,charge,original,amount,currency,policy,warehouse) VALUES('ret','4127','customer@example.invalid','ch',10000,3000,'usd','v1',1)")
        db.execute("INSERT INTO contacts VALUES('contact','fixture','event','ret',1)")
    return db, Fake(tmp_path / "provider.sqlite")
