from dataclasses import dataclass


@dataclass
class timerClassParameters:
    method_name: str = ("",)
    process_name: str = ("",)
    frequency_minutes: int = (60,)
    max_executions: int = (1,)
    run_on_completion_only: bool = (False,)
    minutes_between_heartbeats: int = 10
