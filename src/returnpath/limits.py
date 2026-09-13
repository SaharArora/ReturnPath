"""Durable per-state daily activity reservations before connected calls."""
import datetime


def reserve(db, kind, maximum):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    db.execute('CREATE TABLE IF NOT EXISTS activity (day TEXT, kind TEXT, count INTEGER NOT NULL, PRIMARY KEY(day,kind))')
    db.commit()
    with db:
        db.execute('INSERT OR IGNORE INTO activity VALUES(?,?,0)', (day, kind))
        changed = db.execute('UPDATE activity SET count=count+1 WHERE day=? AND kind=? AND count<?', (day, kind, maximum)).rowcount
        if not changed:
            raise ValueError('Daily controlled-demo activity limit reached: ' + kind)
