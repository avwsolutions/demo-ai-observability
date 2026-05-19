# observability.py

import os
import base64

import sentry_sdk

from sentry_sdk.integrations.flask import (
    FlaskIntegration
)

# -------------------------------------------------------------------
# Sentry SDK
# -------------------------------------------------------------------

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],

    integrations=[
        FlaskIntegration(),
    ],

    traces_sample_rate=1.0,

    profiles_sample_rate=1.0,

    send_default_pii=True,
)

# -------------------------------------------------------------------
# OpenTelemetry
# -------------------------------------------------------------------

from opentelemetry import trace

from opentelemetry.sdk.resources import (
    Resource
)

# Tracing
from opentelemetry.sdk.trace import (
    TracerProvider,
    ReadableSpan
)

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanProcessor,
)

# OTLP Exporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter
)

# -------------------------------------------------------------------
# Instrumentation
# -------------------------------------------------------------------

from opentelemetry.instrumentation.flask import (
    FlaskInstrumentor
)

from opentelemetry.instrumentation.requests import (
    RequestsInstrumentor
)

# -------------------------------------------------------------------
# OpenInference / LangChain
# -------------------------------------------------------------------

from openinference.instrumentation.langchain import (
    LangChainInstrumentor
)

# -------------------------------------------------------------------
# Langfuse SDK
# -------------------------------------------------------------------

from langfuse import Langfuse


# -------------------------------------------------------------------
# Resource
# -------------------------------------------------------------------

resource = Resource.create(
    {
        "service.name": "langgraph-ollama-app",
        "service.version": "1.0.0",
        "deployment.environment": "development",
    }
)


# -------------------------------------------------------------------
# Langfuse Auth
# -------------------------------------------------------------------

langfuse_auth = base64.b64encode(
    (
        f"{os.environ['LANGFUSE_PUBLIC_KEY']}:"
        f"{os.environ['LANGFUSE_SECRET_KEY']}"
    ).encode()
).decode()


# -------------------------------------------------------------------
# OpenTelemetry Trace Provider
# -------------------------------------------------------------------

provider = TracerProvider(
    resource=resource
)

trace.set_tracer_provider(
    provider
)


# -------------------------------------------------------------------
# Langfuse OTLP Trace Exporter
# -------------------------------------------------------------------

langfuse_exporter = OTLPSpanExporter(

    endpoint=(
        f"{os.environ['LANGFUSE_BASE_URL']}"
        "/api/public/otel/v1/traces"
    ),

    headers={
        "Authorization":
            f"Basic {langfuse_auth}"
    }
)


# -------------------------------------------------------------------
# Filter Processor
#
# Prevent Flask / HTTP spans from going to Langfuse
# -------------------------------------------------------------------

class LangfuseFilterSpanProcessor(
    SpanProcessor
):

    def __init__(self, exporter):

        self.processor = BatchSpanProcessor(
            exporter
        )

    def on_start(
        self,
        span,
        parent_context=None
    ):

        self.processor.on_start(
            span,
            parent_context
        )

    def on_end(
        self,
        span: ReadableSpan
    ):

        excluded_scopes = {
            "opentelemetry.instrumentation.flask",
            "opentelemetry.instrumentation.wsgi",
            "opentelemetry.instrumentation.requests",
        }

        scope_name = ""

        if span.instrumentation_scope:
            scope_name = (
                span.instrumentation_scope.name
            )

        # Skip Flask spans
        if scope_name in excluded_scopes:
            return

        # Skip generic HTTP spans
        if "http.method" in span.attributes:
            return

        # Export AI spans only
        self.processor.on_end(span)

    def shutdown(self):

        self.processor.shutdown()

    def force_flush(
        self,
        timeout_millis=30000
    ):

        return self.processor.force_flush(
            timeout_millis
        )


# -------------------------------------------------------------------
# Register Langfuse Span Processor
# -------------------------------------------------------------------

provider.add_span_processor(
    LangfuseFilterSpanProcessor(
        langfuse_exporter
    )
)


# -------------------------------------------------------------------
# Instrumentation
# -------------------------------------------------------------------

RequestsInstrumentor().instrument()

LangChainInstrumentor().instrument()


def instrument_flask(app):

    FlaskInstrumentor().instrument_app(
        app
    )


# -------------------------------------------------------------------
# Langfuse SDK v4
# -------------------------------------------------------------------

langfuse = Langfuse(
    public_key=os.environ[
        "LANGFUSE_PUBLIC_KEY"
    ],

    secret_key=os.environ[
        "LANGFUSE_SECRET_KEY"
    ],

    host=os.environ[
        "LANGFUSE_BASE_URL"
    ]
)