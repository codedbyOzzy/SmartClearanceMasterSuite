# -*- coding: utf-8 -*-
"""Hafif paket: gizli anahtar yoksa boş döner."""


def get_secret(name: str, default: str = "") -> str:
    import os

    env_key = name.upper()
    return os.environ.get(env_key) or os.environ.get(name) or default
