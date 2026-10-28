"""In-memory fakes of ``retro`` and the registry the contract suites iterate over.

Each Protocol of ``api.py`` (and of the consumer port ``CharterHistory``) has its fake here, added by the commit that implements the Protocol: the real
classes and the fake pass the same contract suite (``tests/test_contract_*.py``), so a consumer's unit test may use the fake.
"""

from __future__ import annotations
