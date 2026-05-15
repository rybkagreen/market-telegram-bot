"""Blogger registry verification method enum (BL-107 / ФЗ-303)."""

from enum import StrEnum


class BloggerRegistryVerificationMethod(StrEnum):
    """How channel registry verification was established.

    Per ФЗ-303 от 08.08.2024 channels ≥10k subscribers must register
    в Roskomnadzor blogger registry. Verification has two paths:

    - TRUSTCHANNELBOT_ADMIN: automatic — @Trustchannelbot bot is admin
      of the channel (RKN persistent admin role после successful
      registration via Госуслуги + @Trustchannelbot)
    - MANUAL_EVIDENCE: admin verified owner-submitted evidence
      (application_number от Госуслуги, registry URL, screenshot)
      — fallback path для channels registered via Госуслуги-link
      method без @Trustchannelbot в admins
    """

    TRUSTCHANNELBOT_ADMIN = "trustchannelbot_admin"
    MANUAL_EVIDENCE = "manual_evidence"
