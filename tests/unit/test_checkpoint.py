import json

from evaluation.checkpoint import RunCheckpoint


def test_new_checkpoint_is_empty(tmp_path):
    checkpoint = RunCheckpoint(path=tmp_path / "checkpoint.json")

    assert len(checkpoint) == 0
    assert "any_case" not in checkpoint


def test_record_persists_immediately_to_disk(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = RunCheckpoint(path=path)

    checkpoint.record("case_a", {"answer": "grounded answer"})

    assert path.exists()
    with open(path) as f:
        saved = json.load(f)
    assert saved["results"]["case_a"]["answer"] == "grounded answer"


def test_reloading_checkpoint_resumes_prior_progress(tmp_path):
    path = tmp_path / "checkpoint.json"
    first = RunCheckpoint(path=path)
    first.record("case_a", {"answer": "a"})
    first.record("case_b", {"answer": "b"})

    resumed = RunCheckpoint(path=path)

    assert len(resumed) == 2
    assert "case_a" in resumed
    assert "case_b" in resumed
    assert resumed.results["case_b"]["answer"] == "b"


def test_a_partial_run_only_needs_the_remaining_cases_replayed(tmp_path):
    """This is the actual resume scenario: 38 cases total, a run stops
    after 10 (e.g. hitting a rate limit), and a second process picks the
    checkpoint back up -- it should see exactly the 28 remaining case
    names as not-yet-done.
    """
    path = tmp_path / "checkpoint.json"
    checkpoint = RunCheckpoint(path=path)
    all_case_names = [f"case_{i}" for i in range(38)]
    for name in all_case_names[:10]:
        checkpoint.record(name, {"answer": f"answer for {name}"})

    resumed = RunCheckpoint(path=path)
    remaining = [name for name in all_case_names if name not in resumed]

    assert len(resumed) == 10
    assert len(remaining) == 28
    assert remaining[0] == "case_10"


def test_discard_removes_checkpoint_file(tmp_path):
    path = tmp_path / "checkpoint.json"
    checkpoint = RunCheckpoint(path=path)
    checkpoint.record("case_a", {"answer": "a"})
    assert path.exists()

    checkpoint.discard()

    assert not path.exists()
    assert len(checkpoint) == 0


def test_archive_and_clear_writes_timestamped_run_and_latest_and_clears_checkpoint(
    tmp_path, monkeypatch
):
    from evaluation import checkpoint as checkpoint_module

    monkeypatch.setattr(checkpoint_module, "LATEST_PATH", tmp_path / "latest.json")

    path = tmp_path / "checkpoint.json"
    run = RunCheckpoint(path=path)
    run.record("case_a", {"answer": "a"})
    report = {"hallucination_rate": 0.05, "total_queries": 1}

    archive_path = run.archive_and_clear(report)

    assert archive_path.exists()
    assert not path.exists()
    with open(archive_path) as f:
        archived = json.load(f)
    assert archived["report"] == report
    assert archived["results"]["case_a"]["answer"] == "a"

    latest_path = tmp_path / "latest.json"
    assert latest_path.exists()
    with open(latest_path) as f:
        latest = json.load(f)
    assert latest["report"] == report
