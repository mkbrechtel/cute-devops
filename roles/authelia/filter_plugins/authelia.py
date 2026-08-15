# SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
# SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
#
# SPDX-License-Identifier: EUPL-1.2

"""Filters for the authelia role."""

import base64
import hashlib

DOCUMENTATION = """
name: authelia_pbkdf2_digest
short_description: PBKDF2-SHA512 digest in the format Authelia accepts for OIDC client secrets
description:
  - Produces C($pbkdf2-sha512$<iterations>$<salt>$<hash>) as C(authelia crypto hash generate pbkdf2) would,
    but with a salt derived from the salt argument so repeated renders give the same digest.
options:
  _input:
    description: The plaintext client secret.
    type: str
    required: true
  salt:
    description: A string the 16-byte salt is derived from, typically the client id.
    type: str
    required: true
  iterations:
    description: PBKDF2 iteration count.
    type: int
    default: 310000
"""

EXAMPLES = """
client_secret: "{{ secret | authelia_pbkdf2_digest(client_id) }}"
"""

RETURN = """
_value:
  description: The digest string.
  type: str
"""


def _ab64(data):
    return base64.b64encode(data).decode().replace("+", ".").rstrip("=")


def authelia_pbkdf2_digest(secret, salt, iterations=310000):
    salt_bytes = hashlib.sha256(salt.encode()).digest()[:16]
    dk = hashlib.pbkdf2_hmac("sha512", secret.encode(), salt_bytes, int(iterations))
    return "$pbkdf2-sha512$%d$%s$%s" % (int(iterations), _ab64(salt_bytes), _ab64(dk))


class FilterModule(object):
    def filters(self):
        return {"authelia_pbkdf2_digest": authelia_pbkdf2_digest}
