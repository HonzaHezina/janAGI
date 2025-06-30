"""
Stock Analyzer with Orchestrator and EvaluatorOptimizerLLM Workflow
------------------------------------------------------------
An integrated financial analysis tool using the latest orchestrator implementation
that now supports AugmentedLLM components directly.
"""

import asyncio
import os
import sys
from datetime import datetime
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.orchestrator.orchestrator import Orchestrator
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.workflows.evaluator_optimizer.evaluator_optimizer import (
    EvaluatorOptimizerLLM,
    QualityRating,
)

# Configuration values
OUTPUT_DIR = "company_reports"
COMPANY_NAME = "Apple" if len(sys.argv) <= 1 else sys.argv[1]
MAX_ITERATIONS = 3

# Initialize app
app = MCPApp(name="unified_stock_analyzer", human_input_callback=None)


async def main():
    # Create output directory and set up file paths
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{COMPANY_NAME.lower().replace(' ', '_')}_report_{timestamp}.md"
    output_path = os.path.join(OUTPUT_DIR, output_file)

    async with app.run() as analyzer_app:
        context = analyzer_app.context
        logger = analyzer_app.logger

        # Configure filesystem server to use current directory
        if "filesystem" in context.config.mcp.servers:
            context.config.mcp.servers["filesystem"].args.extend([os.getcwd()])
            logger.info("Filesystem server configured")
        else:
            logger.warning("Filesystem server not configured - report saving may fail")

        # Check for g-search server
        if "g-search" not in context.config.mcp.servers:
            logger.warning(
                "Google Search server not found! This script requires g-search-mcp"
            )
            logger.info("You can install it with: npm install -g g-search-mcp")
            return False

        # --- DEFINE AGENTS ---

        # Research agent: Collects data using Google Search
        research_agent = Agent(
            name="search_finder",
            instruction=f"""Use Google Search to find information about {COMPANY_NAME} in the current month of May 2025:
            You are a world class research analyst.
            Execute these exact search queries:
            1. "{COMPANY_NAME} stock price today"
            2. "{COMPANY_NAME} latest quarterly earnings"
            3. "{COMPANY_NAME} financial news"
            4. "{COMPANY_NAME} earnings expectations"
            
            Extract the most relevant information about:
            - Current stock price and recent movement
            - Latest earnings report data
            - Any significant recent news with correct citations
            
            Be smart and concise. Keep responses short and focused on facts.""",
            server_names=["g-search", "fetch"],
        )

        # Research evaluator: Evaluates the quality of research
        research_evaluator = Agent(
            name="research_evaluator",
            instruction=f"""You are an expert research evaluator specializing in financial data quality.
            
            Evaluate the research data on {COMPANY_NAME} based on these criteria:
            
            1. Accuracy: Are facts properly cited with source URLs? Are numbers precise?
            2. Completeness: Is all required information present? (stock price, earnings data, recent news)
            3. Specificity: Are exact figures provided rather than generalizations?
            4. Clarity: Is the information organized and easy to understand?
            
            For each criterion, provide a rating:
            - EXCELLENT: Exceeds requirements, highly reliable
            - GOOD: Meets all requirements, reliable
            - FAIR: Missing some elements but usable
            - POOR: Missing critical information, not usable
            
            Provide an overall quality rating and specific feedback on what needs improvement.
            If any critical financial data is missing (stock price, earnings figures), the overall
            rating should not exceed FAIR.""",
        )

        # Create the research EvaluatorOptimizerLLM component
        research_quality_controller = EvaluatorOptimizerLLM(
            optimizer=research_agent,
            evaluator=research_evaluator,
            llm_factory=OpenAIAugmentedLLM,
            min_rating=QualityRating.EXCELLENT,
        )

        # Analyst agent: Analyzes the research data
        analyst_agent = Agent(
            name="financial_analyst",
            instruction=f"""Analyze the key financial data for {COMPANY_NAME}:
            You are a world class financial analyst.
            1. Note if stock is up or down and by how much (percentage and dollar amount)
            2. Check if earnings beat or missed expectations (by how much)
            3. List 1-2 main strengths and concerns based on the data
            4. Include any analyst recommendations mentioned in the data
            5. Include any other relevant information that is not covered in the other criteria
            Be specific with numbers and cite any sources of information.""",
            server_names=["fetch"],
        )

        # Report writer: Creates the final report
        report_writer = Agent(
            name="report_writer",
            instruction=f"""Create a professional stock report for {COMPANY_NAME}:
            You are a world class financial report writer.

            Start with a professional header with company name and current date.
            Then in a table format, list the following information:
            - Current stock price and recent movement
            - Latest earnings results and performance vs expectations
            - 1-2 main strengths and concerns based on the data
            
            Create a professional report with the following sections:
            1. Professional header with company name and current date
            2. Brief company description (1-2 sentences)
            3. Current stock performance section with price and recent movement
            4. Latest earnings results section with key metrics
            5. Recent news section with bullet points for relevant developments
            6. Brief outlook and recommendation section
            7. Sources and references section listing all cited sources
            
            Format as clean markdown with appropriate headers and sections.
            Include exact figures with proper formatting (e.g., $XXX.XX, XX%).
            Keep under 800 words total.
            
            Save the report to "{output_path}".""",
            server_names=["filesystem"],
        )

        # --- CREATE THE ORCHESTRATOR ---
        logger.info(f"Initializing stock analysis workflow for {COMPANY_NAME}")

        # The updated Orchestrator can now take AugmentedLLM instances directly
        orchestrator = Orchestrator(
            llm_factory=OpenAIAugmentedLLM,
            available_agents=[
                # We can now pass the EvaluatorOptimizerLLM directly as a component
                research_quality_controller,
                analyst_agent,
                report_writer,
            ],
            plan_type="full",
        )

        # Define the task for the orchestrator
        task = f"""Create a high-quality stock analysis report for {COMPANY_NAME} by following these steps:

        1. Use the EvaluatorOptimizerLLM component (named 'research_quality_controller') to gather high-quality 
           financial data about {COMPANY_NAME}. This component will automatically evaluate 
           and improve the research until it reaches EXCELLENT quality.
           
           Ask for:
           - Current stock price and recent movement
           - Latest quarterly earnings results and performance vs expectations
           - Recent news and developments
        
        2. Use the financial_analyst to analyze this research data and identify key insights.
        
        3. Use the report_writer to create a comprehensive stock report and save it to:
           "{output_path}"
        
        The final report should be professional, fact-based, and include all relevant financial information."""

        # Run the orchestrator
        logger.info("Starting the stock analysis workflow")
        try:
            await orchestrator.generate_str(
                message=task, request_params=RequestParams(model="gpt-4o")
            )

            # Check if report was successfully created
            if os.path.exists(output_path):
                logger.info(f"Report successfully generated: {output_path}")
                return True
            else:
                logger.error(f"Failed to create report at {output_path}")
                return False

        except Exception as e:
            logger.error(f"Error during workflow execution: {str(e)}")
            return False


if __name__ == "__main__":
    asyncio.run(main())
