"""Tests for deliverable presentation reminders in session processing."""

from app.session.processor import _presentation_reminder


def test_presentation_reminder_for_code_execute_deliverables():
    reminder = _presentation_reminder(
        "code_execute",
        {
            "written_files": [
                "/workspace/openyak_written/analyze_helper.py",
                "/workspace/openyak_written/final_report.md",
                "/workspace/openyak_written/final_summary.csv",
            ]
        },
    )

    assert "present_file" in reminder
    assert "final_report.md" in reminder
    assert "final_summary.csv" in reminder
    assert "analyze_helper.py" not in reminder


def test_presentation_reminder_skips_temp_outputs():
    reminder = _presentation_reminder(
        "write",
        {"file_path": "/workspace/openyak_written/temp_notes.md"},
    )

    assert reminder == ""


def test_presentation_reminder_skips_non_file_tools():
    reminder = _presentation_reminder(
        "read",
        {"file_path": "/workspace/openyak_written/final_report.md"},
    )

    assert reminder == ""
