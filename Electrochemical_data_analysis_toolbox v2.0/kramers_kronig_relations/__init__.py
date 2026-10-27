"""Kramers--Kronig validation tools for electrochemical impedance data."""

from .analysis import KKResult, linear_kk
from .io import EISData, load_eis

__all__ = ["EISData", "KKResult", "linear_kk", "load_eis"]
