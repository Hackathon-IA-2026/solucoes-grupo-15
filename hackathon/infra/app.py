#!/usr/bin/env python3
"""Entrada do ``cdk synth``/``cdk deploy`` do CapiWatt (issue #106)."""

from aws_cdk import App

from capiwatt_infra import build_app

app = App()
build_app(app)
app.synth()
