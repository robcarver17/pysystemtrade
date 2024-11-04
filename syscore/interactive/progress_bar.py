import sys
import time

PROGRESS_EXP_FACTOR = 0.9


class progressBar(object):
    """
    Example (not docstring as won't work)

    import time
    thing=progressBar(10000)
    for i in range(10000):
         # do something
         time.sleep(0.001)
         thing.iterate()
    thing.close()

    """

    def __init__(
        self,
        range_to_iterate_over,
        suffix="Progress",
        show_each_time=False,
        show_timings=True,
        toolbar_width: int = 80,
    ):
        self._start_time = time.time()
        self._current_iteration = 0
        self._suffix = suffix
        self._range_to_iterate_over = range_to_iterate_over
        self._range_per_block = range_to_iterate_over / float(toolbar_width)
        self._how_many_blocks_displayed = -1  # will always display first time
        self._show_each_time = show_each_time
        self._show_timings = show_timings

        self._display_bar()

    ### FUNCTION CALLED EACH TIME
    def iterate(self):
        self._add_one_to_current_iteration()
        self._update_time_estimate()
        self._display_bar()
        self._update_iteration_time()  ## must do this after time estimate not before
        if self._check_if_finished():
            self.close()

    def _add_one_to_current_iteration(self):
        self._current_iteration += 1

    def _update_time_estimate(self):
        ## don't maintain a list per se, instead exponential
        time_since_last_call = self._elapsed_time_since_last_called()
        current_estimate = self.current_estimate_of_times
        if current_estimate is None:
            ## seed the current estimate
            current_estimate = time_since_last_call
        else:
            current_estimate = ((1 - PROGRESS_EXP_FACTOR) * time_since_last_call) + (
                PROGRESS_EXP_FACTOR * current_estimate
            )

        self.current_estimate_of_times = current_estimate

    def _display_bar(self):
        ## only show the bar if the number of blocks has changed, or we are showing every time
        if not (
            self._has_number_of_blocks_changed_since_last_displayed()
            or self.show_each_time
        ):
            return None

        _display_progress_bar(self)

        self.how_many_blocks_displayed = self._how_many_blocks_done()

    def _update_iteration_time(self):
        self._time_of_last_iteration = time.time()

    def _check_if_finished(self) -> bool:
        return self.current_iteration == self.range_to_iterate_over

    def _estimated_time_remaining(self) -> float:
        total_iterations = self.range_to_iterate_over
        iterations_left = total_iterations - self.current_iteration
        time_per_iteration = self.current_estimate_of_times
        if time_per_iteration is None:
            return 0

        return iterations_left * time_per_iteration

    def _elapsed_time_since_last_called(self) -> float:
        time_of_last_iteration = self.time_of_last_iteration
        current_time = time.time()

        return current_time - time_of_last_iteration

    def _total_elapsed_time(self) -> float:
        return time.time() - self.start_time

    def _how_many_blocks_done(self) -> int:
        return int(self.current_iteration / self.range_per_block)

    def _how_many_blocks_left(self) -> int:
        return int(
            (self.range_to_iterate_over - self.current_iteration) / self.range_per_block
        )

    def _has_number_of_blocks_changed_since_last_displayed(self) -> bool:
        original_blocks = self.how_many_blocks_displayed
        new_blocks = self._how_many_blocks_done()

        if new_blocks > original_blocks:
            return True
        else:
            return False

    def close(self):
        self._display_bar()
        sys.stdout.write("\n")

    ## state variables
    @property
    def time_of_last_iteration(self) -> time.time:
        time_of_last_iteration = getattr(
            self, "_time_of_last_iteration", self.start_time
        )

        return time_of_last_iteration

    @property
    def current_estimate_of_times(self) -> float:
        current_estimate = getattr(self, "_current_estimate_of_times", None)
        return current_estimate

    @current_estimate_of_times.setter
    def current_estimate_of_times(self, current_estimate: float):
        self._current_estimate_of_times = current_estimate

    @property
    def current_iteration(self):
        return self._current_iteration

    @property
    def start_time(self):
        return self._start_time

    @property
    def suffix(self) -> str:
        return self._suffix

    @property
    def range_to_iterate_over(self) -> int:
        return self._range_to_iterate_over

    @property
    def range_per_block(self) -> int:
        return self._range_per_block

    @property
    def show_each_time(self) -> bool:
        return self._show_each_time

    @property
    def show_timings(self) -> bool:
        return self._show_timings

    @property
    def how_many_blocks_displayed(self) -> int:
        return self._how_many_blocks_displayed

    @how_many_blocks_displayed.setter
    def how_many_blocks_displayed(self, how_many: int):
        self._how_many_blocks_displayed = how_many


def _display_progress_bar(progress_bar: progressBar):
    percents = round(
        100.0
        * progress_bar.current_iteration
        / float(progress_bar.range_to_iterate_over),
        1,
    )
    time_str = _construct_timing_string(progress_bar)
    bar = (
        "=" * progress_bar._how_many_blocks_done()
        + "-" * progress_bar._how_many_blocks_left()
    )
    progress_string = "\0\r [%s] %s%s %s %s" % (
        bar,
        percents,
        "%",
        progress_bar.suffix,
        time_str,
    )
    sys.stdout.write(progress_string)
    sys.stdout.flush()


def _construct_timing_string(progress_bar: progressBar) -> str:
    if progress_bar.show_timings:
        time_remaining = progress_bar._estimated_time_remaining()
        time_elapsed = progress_bar._total_elapsed_time()
        total_est_time = time_elapsed + time_remaining
        time_str = "(%.1f/%.1f/%.1f secs left/elapsed/total)" % (
            time_remaining,
            time_elapsed,
            total_est_time,
        )
    else:
        time_str = ""

    return time_str
