"""OpenTelemetry SDK bootstrap for the Duecare engine.

Configures a global Tracer + Meter from environment variables and
exposes ``trace_span`` / ``record_metric`` helpers that downstream
modules use to instrument their hot paths.

If `opentelemetry-sdk` is missing, all helpers degrade to no-ops so
the engine still runs in lean / development environments.

Environment variables:

  DUECARE_OTEL_ENABLED       — "true" / "false" (default: false)
  DUECARE_OTEL_ENDPOINT      — OTLP receiver, e.g.
                                 http://otel-collector:4318
                                 (HTTP) or grpc://otel-collector:4317
  DUECARE_OTEL_PROTOCOL      — "http/protobuf" | "grpc" (default: http/protobuf)
  DUECARE_OTEL_SERVICE_NAME  — default: "duecare-engine"
  DUECARE_OTEL_ENV           — env tag (default: "local")
  OTEL_RESOURCE_ATTRIBUTES   — passed through to the SDK as-is

Usage:

    from duecare.engine import otel
    otel.bootstrap()

    with otel.trace_span("model.generate", attributes={"model": "gemma4:e2b"}):
        ... call the model ...

The SDK is initialized exactly once on first ``bootstrap()`` call;
subsequent calls are no-ops.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional

_BOOTSTRAPPED = False
_LOCK = threading.Lock()
_TRACER: Any = None
_OTEL_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _OTEL_AVAILABLE = True
except ImportError:                              # pragma: no cover
    pass


def _truthy(v: str | None) -> bool:
    return (v or "").lower() in ("1", "true", "yes", "on")


def bootstrap() -> None:
    """Initialize the global tracer (idempotent + safe to call from
    library code). No-op when OTel SDK is not installed or
    DUECARE_OTEL_ENABLED is false."""
    global _BOOTSTRAPPED, _TRACER
    if _BOOTSTRAPPED:
        return
    with _LOCK:
        if _BOOTSTRAPPED:
            return
        _BOOTSTRAPPED = True

        if not _OTEL_AVAILABLE:
            return
        if not _truthy(os.environ.get("DUECARE_OTEL_ENABLED")):
            return

        endpoint = os.environ.get(
            "DUECARE_OTEL_ENDPOINT",
            "http://otel-collector:4318",
        ).rstrip("/")
        protocol = os.environ.get(
            "DUECARE_OTEL_PROTOCOL", "http/protobuf",
        ).lower()
        service_name = os.environ.get(
            "DUECARE_OTEL_SERVICE_NAME", "duecare-engine",
        )
        env_tag = os.environ.get("DUECARE_OTEL_ENV", "local")

        resource = Resource.create({
            "service.name": service_name,
            "service.namespace": "duecare",
            "deployment.environment": env_tag,
        })
        provider = TracerProvider(resource=resource)

        try:
            if protocol.startswith("grpc"):
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            else:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                # The OTLP HTTP receiver expects /v1/traces appended.
                http_endpoint = endpoint
                if not http_endpoint.endswith("/v1/traces"):
                    http_endpoint = f"{endpoint}/v1/traces"
                exporter = OTLPSpanExporter(endpoint=http_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:                      # pragma: no cover
            # Exporter package missing — fall through with a noop
            # processor so spans get created but not shipped.
            pass

        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("duecare.engine")


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
) -> Iterator[Any]:
    """Open a span. Safe to call before bootstrap() — yields a
    no-op context manager if OTel SDK / endpoint isn't ready."""
    bootstrap()
    if _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                # OTel attribute values must be primitive — coerce
                if not isinstance(v, (str, bool, int, float)):
                    v = str(v)
                span.set_attribute(k, v)
        yield span


def add_event(name: str, attributes: Optional[dict[str, Any]] = None) -> None:
    """Add an event to the currently-active span. No-op if no span."""
    if not _OTEL_AVAILABLE:
        return
    span = trace.get_current_span() if _OTEL_AVAILABLE else None
    if span is None or not span.is_recording():
        return
    span.add_event(name, attributes=attributes or {})


def shutdown() -> None:
    """Flush + close the tracer provider. Call at process exit if you
    don't want spans to be dropped on a hard shutdown."""
    if not _OTEL_AVAILABLE:
        return
    provider = trace.get_tracer_provider() if _OTEL_AVAILABLE else None
    if provider and hasattr(provider, "shutdown"):
        provider.shutdown()
