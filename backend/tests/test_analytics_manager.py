"""Tests for AnalyticsManager counters."""

from datetime import date

from utils.analytics_manager import AnalyticsManager


class Clock:
    def __init__(self, day: date):
        self.day = day

    def __call__(self) -> date:
        return self.day


async def test_counts_are_aggregated_per_day(tmp_path):
    am = AnalyticsManager(data_dir=str(tmp_path), today=Clock(date(2026, 10, 7)))

    await am.record_room_created()
    await am.record_join("u1", 1)
    await am.record_join("u2", 2)
    await am.record_join("u1", 2)
    await am.record_reveal(["8", "coffee"], participants=2, auto=True)

    summary = am.get_summary()
    day = summary["days"][0]
    assert day["date"] == "2026-10-07"
    assert day["active_users"] == 2
    assert day["joins"] == 3
    assert day["peak_room_size"] == 2
    assert summary["totals"]["rounds_revealed"] == 1
    assert summary["totals"]["auto_reveals"] == 1
    assert summary["vote_distribution"] == {"8": 1, "coffee": 1}


async def test_previous_days_user_ids_are_compacted(tmp_path):
    clock = Clock(date(2026, 10, 7))
    am = AnalyticsManager(data_dir=str(tmp_path), today=clock)
    await am.record_join("u1", 1)

    clock.day = date(2026, 10, 8)
    await am.record_join("u2", 1)

    assert "user_ids" not in am.days["2026-10-07"]
    assert am.days["2026-10-07"]["active_users"] == 1
    assert am.days["2026-10-08"]["user_ids"] == ["u2"]


async def test_data_survives_reload(tmp_path):
    clock = Clock(date(2026, 10, 7))
    am = AnalyticsManager(data_dir=str(tmp_path), today=clock)
    await am.record_room_created()

    reloaded = AnalyticsManager(data_dir=str(tmp_path), today=clock)
    await reloaded.load()

    assert reloaded.get_summary()["totals"]["rooms_created"] == 1


async def test_summary_lists_newest_day_first(tmp_path):
    clock = Clock(date(2026, 10, 1))
    am = AnalyticsManager(data_dir=str(tmp_path), today=clock)
    await am.record_room_created()
    clock.day = date(2026, 10, 5)
    await am.record_room_created()

    assert [d["date"] for d in am.get_summary()["days"]] == ["2026-10-05", "2026-10-01"]
