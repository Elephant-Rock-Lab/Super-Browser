"""Tests for BATCH-11 structured logging (M34).

TEST-11-02-04: Structured log entry has correlation_id, timestamp, level
TEST-11-02-05: Log entries are valid JSON
TEST-11-02-06: Correlation ID propagated across agent loop iterations
"""

import json
import logging

from super_browser.agent.structured_logging import (
    StructuredFormatter,
    setup_structured_logging,
)

# -- Helpers ----------------------------------------------------------------

def _make_record(msg: str = "hello", level: int = logging.INFO, **extra):
    """Create a synthetic LogRecord for formatter tests."""
    record = logging.LogRecord(
        name="test",
        level=level,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


# -- Tests ------------------------------------------------------------------


class TestStructuredLogEntry:
    """TEST-11-02-04: Structured log entry has correlation_id, timestamp, level."""

    def test_has_correlation_id(self):
        fmt = StructuredFormatter(correlation_id="abc-123")
        output = fmt.format(_make_record("test msg"))
        data = json.loads(output)
        assert data["correlation_id"] == "abc-123"

    def test_has_timestamp(self):
        fmt = StructuredFormatter(correlation_id="cid")
        output = fmt.format(_make_record("msg"))
        data = json.loads(output)
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO-8601

    def test_has_level(self):
        fmt = StructuredFormatter(correlation_id="cid")
        output = fmt.format(_make_record("msg", level=logging.WARNING))
        data = json.loads(output)
        assert data["level"] == "WARNING"

    def test_has_message(self):
        fmt = StructuredFormatter(correlation_id="cid")
        output = fmt.format(_make_record("hello world"))
        data = json.loads(output)
        assert data["message"] == "hello world"

    def test_correlation_id_from_record_extra(self):
        fmt = StructuredFormatter(correlation_id="default-cid")
        output = fmt.format(_make_record("msg", correlation_id="override-cid"))
        data = json.loads(output)
        assert data["correlation_id"] == "override-cid"


class TestLogEntryJSON:
    """TEST-11-02-05: Log entries are valid JSON."""

    def test_output_is_valid_json(self):
        fmt = StructuredFormatter(correlation_id="test")
        output = fmt.format(_make_record("simple message"))
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_extra_fields_included(self):
        fmt = StructuredFormatter(correlation_id="test")
        output = fmt.format(_make_record("msg", step_number=5, action="click"))
        data = json.loads(output)
        assert data["step_number"] == 5
        assert data["action"] == "click"

    def test_non_serializable_extra_converted_to_string(self):
        fmt = StructuredFormatter(correlation_id="test")

        class Unserializable:
            def __str__(self):
                return "<obj>"

        output = fmt.format(_make_record("msg", weird=Unserializable()))
        data = json.loads(output)
        assert data["weird"] == "<obj>"

    def test_multiple_entries_all_valid_json(self):
        fmt = StructuredFormatter(correlation_id="batch-test")
        for i in range(10):
            output = fmt.format(_make_record(f"msg-{i}", step=i))
            data = json.loads(output)
            assert data["message"] == f"msg-{i}"


class TestCorrelationIDPropagation:
    """TEST-11-02-06: Correlation ID propagated across agent loop iterations."""

    def test_setup_returns_correlation_id(self):
        cid = setup_structured_logging(logger_name="test.propagate.1")
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_setup_uses_provided_correlation_id(self):
        cid = setup_structured_logging("my-custom-cid", logger_name="test.propagate.2")
        assert cid == "my-custom-cid"

    def test_correlation_id_consistent_across_records(self):
        cid = "consistent-cid-123"
        fmt = StructuredFormatter(correlation_id=cid)
        outputs = []
        for i in range(5):
            outputs.append(fmt.format(_make_record(f"step {i}")))
        cids = [json.loads(o)["correlation_id"] for o in outputs]
        assert all(c == cid for c in cids)

    def test_formatter_propagates_cid_to_all_log_lines(self):
        cid = "prop-test-cid"
        fmt = StructuredFormatter(correlation_id=cid)
        line1 = json.loads(fmt.format(_make_record("first")))
        line2 = json.loads(fmt.format(_make_record("second")))
        line3 = json.loads(fmt.format(_make_record("third")))
        assert line1["correlation_id"] == cid
        assert line2["correlation_id"] == cid
        assert line3["correlation_id"] == cid
