import json
import sqlite3

import pytest

from returnpath.policy import decide
from returnpath.worker import tick


def oracle(provider):
    # Deliberately uses raw provider database, no planner, app flags or app journal.
    rows = provider.db.execute("SELECT * FROM refunds").fetchall()
    assert len(rows) == 1
    assert sum(r["amount"] for r in rows) == 3000
    assert rows[0]["charge"] == "ch"
    assert rows[0]["currency"] == "usd"
    return rows


def test_F01_F02_F03_baseline_duplicate_contacts(world):
    db, p = world
    tick(db, p, 100)
    tick(db, p, 101)
    with db:
        db.execute("INSERT OR IGNORE INTO contacts VALUES('contact','fixture','event','ret',1)")
        db.execute("INSERT INTO contacts VALUES('followup','email','other','ret',0)")
    tick(db, p, 102)
    oracle(p)
    assert db.execute("SELECT count(*) FROM operations").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM contacts").fetchone()[0] == 2
    assert p.db.execute("SELECT count(*) FROM mail").fetchone()[0] == 1
    assert 'provider reports' in p.db.execute("SELECT body FROM mail").fetchone()[0]
    assert p.db.execute("SELECT count(*) FROM slack").fetchone()[0] == 1


@pytest.mark.parametrize('warehouse', [None, 0])
def test_F09_F10_warehouse(world, warehouse):
    db, p = world
    with db:
        db.execute("UPDATE cases SET warehouse=?", (warehouse,))
    tick(db, p, 100)
    assert p.db.execute("SELECT count(*) FROM refunds").fetchone()[0] == 0


def test_F11_unavailable_listing(world):
    db, p = world
    def fail(charge):
        raise TimeoutError()
    p.observe = fail
    tick(db, p, 100)
    assert db.execute("SELECT count(*) FROM operations").fetchone()[0] == 0


@pytest.mark.parametrize('status', ['pending', 'failed', 'canceled', 'requires_action'])
def test_F12_F13_non_success(world, status):
    db, p = world
    tick(db, p, 100)
    with p.db:
        p.db.execute("UPDATE refunds SET status=?", (status,))
    tick(db, p, 101)
    oracle(p)
    assert p.db.execute("SELECT count(*) FROM mail").fetchone()[0] == 0
    assert db.execute("SELECT hold FROM cases").fetchone()[0] == (status != 'pending')


def test_F14_corrupt_cached_summary(world):
    db, p = world
    with db:
        db.execute("UPDATE cases SET summary='RESOLVED'")
    tick(db, p, 100)
    tick(db, p, 101)
    oracle(p)


def test_oracle_detects_duplicate_F17(world):
    db, p = world
    tick(db, p, 100)
    op = dict(db.execute("SELECT * FROM operations").fetchone())
    op['idem'] = 'different-key'
    p.refund(op, json.loads(op['params']))
    with pytest.raises(AssertionError):
        oracle(p)
    tick(db, p, 101)
    assert db.execute("SELECT hold FROM cases").fetchone()[0] == 1
    assert p.db.execute("SELECT count(*) FROM refunds").fetchone()[0] == 2


def test_F18_F19_bounded_unknown_same_key(world):
    db, p = world
    keys = []
    def fail(op, params):
        keys.append(op['idem'])
        raise TimeoutError()
    p.refund = fail
    for now in [100, 110, 130, 200, 100000]:
        tick(db, p, now)
    assert len(keys) == 3 and len(set(keys)) == 1
    assert db.execute("SELECT hold FROM cases").fetchone()[0] == 1


def test_F24_ambiguous_mail_no_blind_retry(world):
    db, p = world
    send = p.send
    def lost(*args):
        send(*args)
        raise TimeoutError()
    p.send = lost
    tick(db, p, 100)
    tick(db, p, 101)
    tick(db, p, 102)
    assert p.db.execute("SELECT count(*) FROM mail").fetchone()[0] == 1
    assert db.execute("SELECT state FROM notifications").fetchone()[0] == 'SUBMITTED'


def test_F25_slack_outage(world):
    db, p = world
    def fail(*args):
        raise TimeoutError()
    p.slack = fail
    tick(db, p, 100)
    tick(db, p, 101)
    oracle(p)
    assert db.execute("SELECT summary FROM cases").fetchone()[0] != 'RESOLVED'


def test_F30_hold_late_success(world):
    db, p = world
    tick(db, p, 100)
    with db:
        db.execute("UPDATE cases SET hold=1")
    tick(db, p, 101)
    oracle(p)
    assert db.execute("SELECT status FROM operations").fetchone()[0] == 'succeeded'
    assert db.execute("SELECT hold FROM cases").fetchone()[0] == 1


def test_journal_immutable(world):
    db, p = world
    tick(db, p, 100)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE operations SET idem='new-key'")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE cases SET amount=6000")


@pytest.mark.parametrize('amount', [True, 30.0, -3000, 0, 6000])
def test_fixed_integer_approval(amount):
    facts = dict(warehouse=True, fetched_at=100, refunds=[], expected_charge='ch', approved=amount,
                 charge=dict(id='ch', livemode=False, amount=10000, currency='usd', paid=True,
                             captured=True, disputed=False, type='card'))
    assert decide(facts, True, None, False, 100).action != 'POST'
