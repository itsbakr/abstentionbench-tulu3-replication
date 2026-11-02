"""withholding.typed: the typed ingestion layer (notes/typed_ingestion_design_2026-10-15.md; decisions in
notes/typed_layer_decisions_2026-10-15.md).

Modules: ``models`` (the types and their invariants, design 2), ``registry`` (TemplateSpec entries and probes),
``legacy`` (the frozen 14 Oct reading), ``ingest`` (classification, delivery, the issuer of sealed texts),
``adapters`` (stored row shapes) and, from step 4, ``report`` (the issuer of cells). Import them by name; this package
imports only ``models``.

Import checks (design 2.0, review item 17): importing the package asserts the pydantic version declared in
pyproject.toml and runs the seal self-check. Either failure raises ImportError before anything scores, locally and in
the runner image.
"""
from withholding.typed import models

models.check_pydantic_version()
models.seal_self_check()

__all__ = ["models"]
