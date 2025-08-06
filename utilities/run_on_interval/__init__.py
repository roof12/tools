"""Make run_on_interval a package and expose its main functions."""
from .run_on_interval import main, non_negative_int, positive_int

__all__ = ["main", "non_negative_int", "positive_int"]
