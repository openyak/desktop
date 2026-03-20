"""Streaming manager tests — GenerationJob lifecycle, interactive mode, permissions."""

import asyncio

import pytest

from app.streaming.events import SSEEvent, TEXT_DELTA, DONE, PERMISSION_REQUEST
from app.streaming.manager import GenerationJob, StreamManager


class TestGenerationJobInteractive:
    """Tests for the interactive permission flow."""

    def test_default_not_interactive(self):
        job = GenerationJob("s1", "sess1")
        assert job.interactive is False

    def test_set_interactive(self):
        job = GenerationJob("s1", "sess1")
        job.interactive = True
        assert job.interactive is True

    def test_default_depth_zero(self):
        job = GenerationJob("s1", "sess1")
        assert job._depth == 0

    @pytest.mark.asyncio
    async def test_wait_for_response(self):
        """Test that wait_for_response receives a submitted response."""
        job = GenerationJob("s1", "sess1")

        async def submit_later():
            await asyncio.sleep(0.05)
            job.submit_response("call-1", "allow")

        asyncio.create_task(submit_later())
        response = await job.wait_for_response("call-1", timeout=5.0)
        assert response == "allow"

    @pytest.mark.asyncio
    async def test_wait_for_response_timeout(self):
        """Test that wait_for_response raises on timeout."""
        job = GenerationJob("s1", "sess1")
        with pytest.raises(TimeoutError):
            await job.wait_for_response("call-1", timeout=0.05)

    @pytest.mark.asyncio
    async def test_submit_before_wait(self):
        """Response submitted before wait_for_response is called."""
        job = GenerationJob("s1", "sess1")
        job.submit_response("call-1", "deny")
        response = await job.wait_for_response("call-1", timeout=1.0)
        assert response == "deny"


class TestStreamManagerCleanup:
    def test_cleanup_completed(self):
        sm = StreamManager()
        # Insert jobs directly to avoid auto-cleanup in create_job
        for i in range(60):
            job = GenerationJob(stream_id=f"s{i}", session_id=f"sess{i}")
            sm._jobs[f"s{i}"] = job
            if i < 55:
                job.complete()

        removed = sm.cleanup_completed(keep_last=10)
        assert removed == 45  # 55 completed, keep 10

    def test_active_jobs_excludes_completed(self):
        sm = StreamManager()
        j1 = sm.create_job("s1", "sess1")
        j2 = sm.create_job("s2", "sess2")
        j1.complete()

        active = sm.active_jobs()
        assert len(active) == 1
        assert active[0]["stream_id"] == "s2"
