from typing import Callable, List, Literal, Optional, TYPE_CHECKING

from opentelemetry import trace
from pydantic import BaseModel

from mcp_agent.agents.agent import Agent
from mcp_agent.tracing.semconv import GEN_AI_REQUEST_TOP_K
from mcp_agent.tracing.telemetry import get_tracer
from mcp_agent.workflows.llm.augmented_llm import AugmentedLLM
from mcp_agent.workflows.router.router_base import ResultT, Router, RouterResult
from mcp_agent.logging.logger import get_logger

if TYPE_CHECKING:
    from mcp_agent.core.context import Context

logger = get_logger(__name__)


DEFAULT_ROUTING_INSTRUCTION = """
You are a highly accurate request router that directs incoming requests to the most appropriate category.
A category is a specialized destination, such as a Function, an MCP Server (a collection of tools/functions), or an Agent (a collection of servers).
Below are the available routing categories, each with their capabilities and descriptions:

{context}

Your task is to analyze the following request and determine the most appropriate categories from the options above. Consider:
- The specific capabilities and tools each destination offers
- How well the request matches the category's description
- Whether the request might benefit from multiple categories (up to {top_k})

Request: {request}

Respond in JSON format:
{{
    "categories": [
        {{
            "category": <category name>,
            "confidence": <high, medium or low>,
            "reasoning": <brief explanation>
        }}
    ]
}}

Only include categories that are truly relevant. You may return fewer than {top_k} if appropriate.
If none of the categories are relevant, return an empty list.
"""


class LLMRouterResult(RouterResult[ResultT]):
    """A class that represents the result of an LLMRouter.route request"""

    confidence: Literal["high", "medium", "low"]
    """The confidence level of the routing decision."""

    reasoning: str | None = None
    """
    A brief explanation of the routing decision.
    This is optional and may only be provided if the router is an LLM
    """


class StructuredResponseCategory(BaseModel):
    """A class that represents a single category returned by an LLM router"""

    category: str
    """The name of the category (i.e. MCP server, Agent or function) to route the input to."""

    confidence: Literal["high", "medium", "low"]
    """The confidence level of the routing decision."""

    reasoning: str | None = None
    """A brief explanation of the routing decision."""


class StructuredResponse(BaseModel):
    """A class that represents the structured response of an LLM router"""

    categories: List[StructuredResponseCategory]
    """A list of categories to route the input to."""


class LLMRouter(Router):
    """
    A router that uses an LLM to route an input to a specific category.
    """

    def __init__(
        self,
        llm: AugmentedLLM,
        server_names: List[str] | None = None,
        agents: List[Agent] | None = None,
        functions: List[Callable] | None = None,
        routing_instruction: str | None = None,
        context: Optional["Context"] = None,
        **kwargs,
    ):
        super().__init__(
            server_names=server_names,
            agents=agents,
            functions=functions,
            routing_instruction=routing_instruction,
            context=context,
            **kwargs,
        )

        self.llm = llm

    @classmethod
    async def create(
        cls,
        llm: AugmentedLLM,
        server_names: List[str] | None = None,
        agents: List[Agent] | None = None,
        functions: List[Callable] | None = None,
        routing_instruction: str | None = None,
        context: Optional["Context"] = None,
    ) -> "LLMRouter":
        """
        Factory method to create and initialize a router.
        Use this instead of constructor since we need async initialization.
        """
        instance = cls(
            llm=llm,
            server_names=server_names,
            agents=agents,
            functions=functions,
            routing_instruction=routing_instruction,
            context=context,
        )
        await instance.initialize()
        return instance

    async def route(
        self, request: str, top_k: int = 1
    ) -> List[LLMRouterResult[str | Agent | Callable]]:
        tracer = get_tracer(self.context)
        with tracer.start_as_current_span(f"{self.__class__.__name__}.route") as span:
            self._annotate_span_for_route_request(span, request, top_k)

            if not self.initialized:
                await self.initialize()

            res = await self._route_with_llm(request, top_k)
            self._annotate_span_for_router_result(span, res)
            return res

    async def route_to_server(
        self, request: str, top_k: int = 1
    ) -> List[LLMRouterResult[str]]:
        tracer = get_tracer(self.context)
        with tracer.start_as_current_span(
            f"{self.__class__.__name__}.route_to_server"
        ) as span:
            self._annotate_span_for_route_request(span, request, top_k)

            if not self.initialized:
                await self.initialize()

            res = await self._route_with_llm(
                request,
                top_k,
                include_servers=True,
                include_agents=False,
                include_functions=False,
            )
            self._annotate_span_for_router_result(span, res)
            return res

    async def route_to_agent(
        self, request: str, top_k: int = 1
    ) -> List[LLMRouterResult[Agent]]:
        tracer = get_tracer(self.context)
        with tracer.start_as_current_span(
            f"{self.__class__.__name__}.route_to_agent"
        ) as span:
            self._annotate_span_for_route_request(span, request, top_k)

            if not self.initialized:
                await self.initialize()

            res = await self._route_with_llm(
                request,
                top_k,
                include_servers=False,
                include_agents=True,
                include_functions=False,
            )
            self._annotate_span_for_router_result(span, res)
            return res

    async def route_to_function(
        self, request: str, top_k: int = 1
    ) -> List[LLMRouterResult[Callable]]:
        tracer = get_tracer(self.context)
        with tracer.start_as_current_span(
            f"{self.__class__.__name__}.route_to_function"
        ) as span:
            self._annotate_span_for_route_request(span, request, top_k)

            if not self.initialized:
                await self.initialize()

            res = await self._route_with_llm(
                request,
                top_k,
                include_servers=False,
                include_agents=False,
                include_functions=True,
            )
            self._annotate_span_for_router_result(span, res)
            return res

    async def _route_with_llm(
        self,
        request: str,
        top_k: int = 1,
        include_servers: bool = True,
        include_agents: bool = True,
        include_functions: bool = True,
    ) -> List[LLMRouterResult]:
        tracer = get_tracer(self.context)
        with tracer.start_as_current_span(
            f"{self.__class__.__name__}._route_with_llm"
        ) as span:
            self._annotate_span_for_route_request(span, request, top_k)

            if not self.initialized:
                await self.initialize()

            routing_instruction = (
                self.routing_instruction or DEFAULT_ROUTING_INSTRUCTION
            )

            # Generate the categories context
            context = self._generate_context(
                include_servers=include_servers,
                include_agents=include_agents,
                include_functions=include_functions,
            )

            # logger.debug(
            #     f"Requesting routing from LLM, \nrequest: {request} \ntop_k: {top_k} \nrouting_instruction: {routing_instruction} \ncontext={context}",
            #     data={"progress_action": "Routing", "agent_name": "LLM Router"},
            # )

            # Format the prompt with all the necessary information
            prompt = routing_instruction.format(
                context=context, request=request, top_k=top_k
            )

            # Get routes from LLM
            response = await self.llm.generate_structured(
                message=prompt,
                response_model=StructuredResponse,
            )

            if self.context.tracing_enabled:
                response_categories_data = {}
                for i, r in enumerate(response.categories):
                    response_categories_data[f"category.{i}.category"] = r.category
                    response_categories_data[f"category.{i}.confidence"] = r.confidence
                    if r.reasoning:
                        response_categories_data[f"category.{i}.reasoning"] = (
                            r.reasoning
                        )

                span.add_event(
                    "routing.response",
                    {
                        "prompt": prompt,
                        **response_categories_data,
                    },
                )

            # logger.debug(
            #     "Routing Response received",
            #     data={"progress_action": "Finished", "agent_name": "LLM Router"},
            # )

            # Construct the result
            if not response or not response.categories:
                return []

            result: List[LLMRouterResult] = []
            for r in response.categories:
                router_category = self.categories.get(r.category)
                if not router_category:
                    # Skip invalid categories
                    # TODO: saqadri - log or raise an error
                    continue

                result.append(
                    LLMRouterResult(
                        result=router_category.category,
                        confidence=r.confidence,
                        reasoning=r.reasoning,
                    )
                )

            self._annotate_span_for_router_result(span, result)

            return result[:top_k]

    def _annotate_span_for_route_request(
        self,
        span: trace.Span,
        request: str,
        top_k: int,
    ):
        """Annotate the span with the request and top_k."""
        if not self.context.tracing_enabled:
            return
        span.set_attribute("request", request)
        span.set_attribute(GEN_AI_REQUEST_TOP_K, top_k)
        span.set_attribute("llm", self.llm.name)
        span.set_attribute(
            "agents", [a.name for a in self.agents] if self.agents else []
        )
        span.set_attribute("servers", self.server_names or [])
        span.set_attribute(
            "functions", [f.__name__ for f in self.functions] if self.functions else []
        )

    def _annotate_span_for_router_result(
        self,
        span: trace.Span,
        result: List[LLMRouterResult],
    ):
        """Annotate the span with the router result."""
        if not self.context.tracing_enabled:
            return
        for i, res in enumerate(result):
            span.set_attribute(f"result.{i}.confidence", res.confidence)
            if res.reasoning:
                span.set_attribute(f"result.{i}.reasoning", res.reasoning)
            if res.p_score:
                span.set_attribute(f"result.{i}.p_score", res.p_score)

            result_key = f"result.{i}.result"
            if isinstance(res.result, str):
                span.set_attribute(result_key, res.result)
            elif isinstance(res.result, Agent):
                span.set_attribute(result_key, res.result.name)
            elif callable(res.result):
                span.set_attribute(result_key, res.result.__name__)

    def _generate_context(
        self,
        include_servers: bool = True,
        include_agents: bool = True,
        include_functions: bool = True,
    ) -> str:
        """Generate a formatted context list of categories."""

        context_list = []
        idx = 1

        # Format all categories
        if include_servers:
            for category in self.server_categories.values():
                context_list.append(self.format_category(category, idx))
                idx += 1

        if include_agents:
            for category in self.agent_categories.values():
                context_list.append(self.format_category(category, idx))
                idx += 1

        if include_functions:
            for category in self.function_categories.values():
                context_list.append(self.format_category(category, idx))
                idx += 1

        return "\n\n".join(context_list)
