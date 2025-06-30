import uuid

from opentelemetry import trace
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from mcp_agent.config import OpenTelemetrySettings
from mcp_agent.logging.logger import get_logger
from mcp_agent.tracing.file_span_exporter import FileSpanExporter

logger = get_logger(__name__)


class TracingConfig:
    """Global configuration for the tracing system."""

    _initialized = False

    @classmethod
    async def configure(
        cls,
        settings: OpenTelemetrySettings,
        session_id: str | None = None,
    ):
        """
        Configure the tracing system.

        Args:
            session_id: Optional session ID for exported traces
            **kwargs: Additional configuration options
        """
        if cls._initialized:
            return

        if not settings.enabled:
            logger.info("OpenTelemetry is disabled. Skipping configuration.")
            return

        # Check if a provider is already set to avoid re-initialization
        if isinstance(trace.get_tracer_provider(), TracerProvider):
            logger.info(
                f"Otel tracer provider already set: {trace.get_tracer_provider().__class__.__name__}"
            )
            return

        # Set up global textmap propagator first
        set_global_textmap(TraceContextTextMapPropagator())

        # pylint: disable=import-outside-toplevel (do not import if otel is not enabled)
        from importlib.metadata import version

        service_version = settings.service_version
        if not service_version:
            try:
                service_version = version("mcp-agent")
            # pylint: disable=broad-exception-caught
            except Exception:
                service_version = "unknown"

        session_id = session_id or str(uuid.uuid4())

        service_name = settings.service_name
        service_instance_id = settings.service_instance_id or session_id

        # Create resource identifying this service
        resource = Resource.create(
            attributes={
                key: value
                for key, value in {
                    "service.name": service_name,
                    "service.instance.id": service_instance_id,
                    "service.version": service_version,
                    "session.id": session_id,
                }.items()
                if value is not None
            }
        )

        # Create provider with resource
        tracer_provider = TracerProvider(resource=resource)

        for exporter in settings.exporters:
            if exporter == "console":
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(
                        ConsoleSpanExporter(service_name=settings.service_name)
                    )
                )
            elif exporter == "otlp":
                if settings.otlp_settings:
                    tracer_provider.add_span_processor(
                        BatchSpanProcessor(
                            OTLPSpanExporter(endpoint=settings.otlp_settings.endpoint)
                        )
                    )
                else:
                    logger.error(
                        "OTLP exporter is enabled but no OTLP settings endpoint is provided."
                    )
            elif exporter == "file":
                tracer_provider.add_span_processor(
                    BatchSpanProcessor(
                        FileSpanExporter(
                            service_name=settings.service_name,
                            session_id=session_id,
                            path_settings=settings.path_settings,
                        )
                    )
                )
                continue
            else:
                logger.error(
                    f"Unknown exporter '{exporter}' specified. Supported exporters: console, otlp, file."
                )

        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Set up autoinstrumentation
        # pylint: disable=import-outside-toplevel (do not import if otel is not enabled)
        try:
            from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

            AnthropicInstrumentor().instrument()
        except ModuleNotFoundError:
            logger.error(
                "Anthropic otel instrumentation not available. Please install opentelemetry-instrumentation-anthropic."
            )
        try:
            from opentelemetry.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument()
        except ModuleNotFoundError:
            logger.error(
                "OpenAI otel instrumentation not available. Please install opentelemetry-instrumentation-anthropic."
            )

        cls._initialized = True
