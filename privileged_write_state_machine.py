#!/usr/bin/env python3
"""Beta 51: non-privileged state machine for testing writer orchestration.

No system D-Bus registration, Polkit authority, root helper or block device writes.
The state machine never accepts a device handle or performs filesystem I/O.
"""
from dataclasses import dataclass
from enum import Enum

class Stage(str, Enum):
    IDLE = "idle"
    PREPARED = "prepared"
    AUTHORIZED = "authorized"
    WRITING = "writing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    FAILED = "failed"

@dataclass(frozen=True)
class Snapshot:
    stage: str
    bytes_written: int
    total_bytes: int
    writing_enabled: bool = False
    physical_device_opened: bool = False

class SimulatedWriteJob:
    """Pure in-memory model, not an authorization or writing API."""
    def __init__(self, total_bytes):
        if type(total_bytes) is not int or not 0 < total_bytes <= 2**63-1:
            raise ValueError("Invalid size")
        self.total = total_bytes
        self.completed = 0
        self.stage = Stage.IDLE

    def snapshot(self):
        return Snapshot(self.stage.value, self.completed, self.total)

    def prepare(self):
        if self.stage != Stage.IDLE:
            raise ValueError("Invalid transition")
        self.stage = Stage.PREPARED
        return self.snapshot()

    def simulate_progress(self, new_total):
        # Never advances to actual writing. No caller can grant authorization.
        raise PermissionError("Physical writer not implemented; progress cannot be simulated as a real write")

    def cancel(self):
        if self.stage in (Stage.COMPLETE, Stage.CANCELLED, Stage.FAILED):
            raise ValueError("Terminal job")
        self.stage = Stage.CANCELLED
        return self.snapshot()

    def fail(self):
        if self.stage in (Stage.COMPLETE, Stage.CANCELLED, Stage.FAILED):
            raise ValueError("Terminal job")
        self.stage = Stage.FAILED
        return self.snapshot()
