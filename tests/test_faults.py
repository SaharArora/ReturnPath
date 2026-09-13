import sqlite3
import pytest
from returnpath.worker import tick


def test_F07_provider_commits_lost_response(world):
    db, provider = world
    original = provider.refund
    def lost(op, params):
        original(op, params)
        raise TimeoutError()
    provider.refund = lost
    tick(db, provider, 100)
    tick(db, provider, 101)
    assert provider.db.execute('SELECT count(*),sum(amount) FROM refunds').fetchone()[:] == (1, 3000)
    assert db.execute('SELECT provider_id FROM operations').fetchone()[0]


def test_F15_unassigned_refund(world):
    db, provider = world
    provider.refund({'id': 'manual', 'case_id': 'unassigned', 'idem': 'external'},
                    {'charge': 'ch', 'amount': 1000, 'currency': 'usd'})
    tick(db, provider, 100)
    assert provider.db.execute('SELECT count(*),sum(amount) FROM refunds').fetchone()[:] == (1, 1000)
    assert db.execute('SELECT hold FROM cases').fetchone()[0] == 1


def test_F27_journal_commit_failure_no_post(world):
    db, provider = world
    db.execute("CREATE TRIGGER deny_attempt BEFORE UPDATE OF first_attempt ON operations BEGIN SELECT RAISE(ABORT,'fault'); END")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        tick(db, provider, 100)
    assert provider.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 0


def test_F18_elapsed_horizon_no_post(world):
    db, provider = world
    def lost(*args):
        raise TimeoutError()
    provider.refund = lost
    tick(db, provider, 100)
    del provider.refund
    tick(db, provider, 100 + 23 * 3600)
    assert provider.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 0
    assert db.execute('SELECT hold FROM cases').fetchone()[0] == 1


def test_unknown_mail_absence_not_proof(world):
    db, provider = world
    count = []
    def lost(*args):
        count.append(1)
        raise TimeoutError()
    provider.send = lost
    tick(db, provider, 100)
    for now in [101, 102, 200000]:
        tick(db, provider, now)
    assert count == [1]
    assert db.execute('SELECT state FROM notifications').fetchone()[0] == 'SEND_UNKNOWN'
