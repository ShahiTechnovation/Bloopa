"""
exceptions.py — Custom exceptions for the Bloopa credit SDK.
"""


class BloopaCreditError(Exception):
    """Base exception for all Bloopa SDK errors.

    Catch this to handle any SDK failure without distinguishing between
    a denial and a technical fault.
    """

    pass


class BloopaCreditDenied(BloopaCreditError):
    """Raised when the risk oracle denies a credit draw request.

    The oracle evaluates four immutable criteria before every draw. If any
    criterion fails, this exception is raised and the on-chain draw() call
    is never made.

    Attributes:
        reason: Plain-English description of which criterion failed and why.
        criteria_results: Full breakdown of all four criteria evaluations as
            a dict (from CriteriaEvaluation.model_dump()). Empty dict when
            the denial happens before the oracle call (e.g. tier cap exceeded).

    Example::

        try:
            result = agent.draw(...)
        except BloopaCreditDenied as e:
            print(f"Credit denied: {e.reason}")
            print(f"Criteria details: {e.criteria_results}")
    """

    def __init__(self, reason: str, criteria_results: dict) -> None:
        """Initialise the denial exception.

        Args:
            reason: Which criterion failed and the specific reason.
            criteria_results: Full dict from CriteriaEvaluation.model_dump(),
                or an empty dict for pre-flight denials (tier cap etc.).
        """
        self.reason = reason
        self.criteria_results = criteria_results
        super().__init__(reason)
