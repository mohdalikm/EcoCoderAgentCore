# Eco-Coder Specifications

This document provides a summarized overview of the Eco-Coder AI Agent's architecture, configuration, and implementation details.

## 1. Project Vision

Eco-Coder is an autonomous AI agent designed to embed environmental impact analysis directly into the software development lifecycle. By providing developers with immediate, actionable feedback on the energy efficiency and estimated carbon footprint of their code changes, Eco-Coder aims to foster a new paradigm of "green coding."

## 2. System Architecture

The Eco-Coder system is designed as a robust, scalable, and secure serverless application on AWS.

- **Orchestration Core**: **Amazon Bedrock Agents** orchestrates the entire workflow, using an LLM (Anthropic's Claude 3 Sonnet) to reason and plan.
- **Hosting**: The agent is hosted on **Amazon Bedrock AgentCore Runtime**, which provides a secure and scalable environment for the agent's container.
- **Tools**: The agent's capabilities are provided by a set of tools, implemented as Python functions within the agent container. These tools interact with services like **Amazon CodeGuru** (for code and performance analysis), **CodeCarbon** (for carbon estimation), and the **GitHub API** (for posting reports).
- **Event-Driven**: The workflow is triggered by a GitHub webhook on a pull request event, which is sent to an **Amazon API Gateway** endpoint that invokes the agent.

## 3. Agent and Tool Configuration

The agent's behavior is defined by a detailed system prompt that instructs it on how to perform its analysis. The prompt specifies a multi-step process:

1.  **Initiate Parallel Analysis**: Start code quality and performance analysis concurrently.
2.  **Wait for Performance Data**: Await results from the performance profiling.
3.  **Calculate Carbon Footprint**: Use performance data to estimate CO2 impact.
4.  **Wait for Code Analysis**: Await results from the code quality scan.
5.  **Synthesize Green Code Report**: Combine all information into a formatted Markdown report.
6.  **Post the Report**: Post the report as a comment on the GitHub pull request.

The report includes an "Eco-Score," carbon footprint analysis, performance bottlenecks, code quality recommendations, and AI-powered refactoring suggestions.

## 4. Implementation Strategy

The project is implemented using the **Strands Agents SDK**, which facilitates the development of framework-agnostic AI agents.

- **Container-First Design**: The agent and all its tools are packaged into a single Docker container, simplifying deployment and reducing complexity. This container is deployed to the AgentCore Runtime.
- **Direct Integration**: The agent's tools make direct calls to AWS services (like CodeGuru) and the GitHub API from within the container, avoiding the need for intermediate Lambda functions.
- **CI/CD**: A GitHub Actions workflow automates the building, testing, and deployment of the agent container to AWS.

This architecture is cost-effective, scalable, and maintainable, providing a robust foundation for the Eco-Coder agent.
