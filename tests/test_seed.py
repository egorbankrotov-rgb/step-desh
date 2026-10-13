from app.seed import seed_demo


def test_seed_demo_is_idempotent(repo):
    seed_demo(repo)
    seed_demo(repo)
    assert len(repo.list_operators()) == 3
    assert len(repo.list_ranges()) == 5
    assert repo.find_range("903", "1234567") is not None
