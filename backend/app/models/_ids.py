"""Identifiers shared by the tables."""
import uuid


def uid():
    return str(uuid.uuid4())
