# **Eco-Coder: An AI Agent for Sustainable Software Development**

## **Part I: Project Vision & Executive Summary**

### **1.1. Introduction: The Agent of Environmental Change**

The digital transformation of the global economy has ushered in an era of unprecedented innovation and connectivity. However, this progress is underpinned by a rapidly expanding physical infrastructure of data centers, which are significant consumers of global energy. The software that runs within these data centers, often developed without consideration for its energy efficiency, is a primary driver of this consumption. Inefficient algorithms, suboptimal data structures, and redundant computations translate directly into increased server utilization, higher energy draw, and consequently, a larger carbon footprint. The software development industry, therefore, stands at a critical juncture, with both the responsibility and the opportunity to mitigate its environmental impact.  
This document outlines a project proposal for the AWS AI Agent Global Hackathon, titled **"Eco-Coder."** This project directly addresses the challenge of sustainable software engineering by introducing a novel AI agent designed to serve as a proactive partner for developers. Eco-Coder's vision is to embed environmental impact analysis directly into the heart of the software development lifecycle: the code review process. By providing developers with immediate, actionable feedback on the energy efficiency and estimated carbon footprint of their code changes, Eco-Coder aims to foster a new paradigm of "green coding." It transforms the abstract concept of software sustainability into a tangible, measurable, and optimizable metric within the developer's existing workflow. In perfect alignment with the hackathon's theme, "Agents of change \- building tomorrows AI solution today," Eco-Coder empowers individual developers to become agents of positive environmental change, enabling them to build the more sustainable digital solutions of tomorrow, one pull request at a time.

### **1.2. Executive Summary**

**Problem:** The software industry is a significant and growing contributor to global carbon emissions, driven by the immense energy consumption of data centers. Developers, who are in the best position to optimize software for energy efficiency, currently lack the necessary tools to measure, understand, and mitigate the environmental impact of their code during the development process. Existing sustainability tools typically operate at the infrastructure level, providing retroactive data that is disconnected from the specific code changes that cause the emissions. This creates a critical feedback gap, preventing the widespread adoption of green software engineering principles.  
**Solution:** Eco-Coder is an autonomous AI agent, built on the Amazon Bedrock platform, that seamlessly integrates into a developer's standard CI/CD pipeline. Triggered by a new pull request in a code repository, the Eco-Coder agent orchestrates a series of analyses to evaluate the proposed code changes. It leverages the power of Amazon CodeGuru to perform deep static analysis and runtime performance profiling, identifying computational inefficiencies, security vulnerabilities, and deviations from best practices. Concurrently, it utilizes the open-source CodeCarbon library to translate these performance metrics into an estimated carbon footprint, quantifying the environmental cost of the code. The agent's core intelligence, powered by a large language model (LLM) from Amazon Bedrock, synthesizes these disparate data streams—performance bottlenecks, code quality issues, and carbon estimates—into a single, coherent, and actionable "Green Code Report." This report is then automatically posted as a comment directly within the developer's pull request, providing context-rich feedback at the most opportune moment.  
**Impact:** Eco-Coder provides immediate, quantifiable, and educational feedback on the environmental impact of software development. By surfacing an "Eco-Score" and concrete CO2e estimates, it makes the environmental cost of code visible and tangible. This empowers developers to make informed decisions, encourages the adoption of energy-efficient coding practices, and drives a cultural shift towards sustainability within engineering teams. The direct result is the development of more performant, cost-effective, and environmentally friendly software, leading to measurable reductions in cloud infrastructure costs and a significant decrease in the carbon footprint of digital services.  
**Technical Stack:** The solution is architected as a serverless, event-driven application on AWS, ensuring scalability and cost-efficiency. The core of the project is **Amazon Bedrock Agents**, which orchestrates the entire workflow. The architecture explicitly utilizes **Amazon Bedrock AgentCore** primitives, including Runtime for secure hosting and Gateway for tool management, as strongly recommended by the hackathon rules. The agent's tools are implemented as **AWS Lambda** functions that interact with external services, including the **Amazon CodeGuru Reviewer and Profiler APIs**, the **CodeCarbon API**, and the **GitHub API**. This technology stack fully complies with all mandatory project requirements for the AWS AI Agent Global Hackathon, positioning the project for high scores in technical execution.

## **Part II: The Problem Domain: Quantifying the Environmental Cost of Code**

### **2.1. The Silent Emitter: Software's Carbon Footprint**

The digital economy's contribution to global energy consumption and carbon emissions is substantial and growing at an alarming rate. Data centers, the backbone of the internet, cloud computing, and AI, are projected to consume an increasingly significant share of the world's electricity. While much attention has been focused on the energy efficiency of hardware and data center operations, the software running on that hardware is an equally critical, yet often overlooked, factor. The design and implementation of software have a direct and profound impact on hardware utilization. Inefficient code—characterized by redundant processing, excessive memory allocation, or poor algorithmic choices—forces CPUs, GPUs, and memory modules to work harder and for longer periods, thereby increasing energy consumption.  
This has given rise to the discipline of Green Software Engineering, an emerging field dedicated to the practice of designing, developing, and deploying software with a minimal environmental impact. Its principles are rooted in the understanding that software is not an abstract entity but a physical process with real-world energy consequences. Every CPU cycle, every byte of data transferred, and every millisecond of latency contributes to the overall energy draw. The cumulative effect of billions of lines of inefficient code running across millions of servers worldwide represents a massive, and largely untapped, opportunity for environmental sustainability. By optimizing code for performance and efficiency, developers can directly reduce the energy demand of their applications, which in turn lessens the load on data centers and lowers the associated carbon emissions.

### **2.2. Deconstructing Software Emissions: The SCI Framework**

To systematically address the environmental impact of software, a standardized measurement framework is essential. The Green Software Foundation, a consortium of technology leaders, has developed the Software Carbon Intensity (SCI) specification to provide a consistent methodology for calculating the carbon emissions of a software application. The SCI is not an absolute measure of total carbon but a rate of carbon emissions per functional unit, allowing for fair comparisons and tracking of improvements over time.  
The core SCI equation is defined as:  
Where:

* **C** is the total carbon emissions, broken down into two components:  
  * **O (Operational Emissions):** The carbon emissions produced by the energy consumed by the hardware while the software is running. This is the primary target for optimization by software developers.  
  * **M (Embodied Emissions):** The carbon emissions generated during the manufacturing and eventual disposal of the hardware components the software runs on. This is amortized over the expected lifespan of the hardware.  
* **R** is the functional unit, which defines the "per" basis of the calculation (e.g., per user, per API call, per device).

The Eco-Coder project focuses specifically on reducing the Operational Emissions (O), as this is the component most directly influenced by code-level optimizations. The calculation for operational emissions is given by:  
Where:

* **E (Energy):** The total electricity (in kWh) consumed by the hardware running the software. This is directly correlated with the software's computational intensity and runtime.  
* **I (Carbon Intensity):** The rate of carbon emissions per unit of energy generated (in gCO2e/kWh). This value varies significantly based on the geographical location of the data center and the energy mix of the local power grid (i.e., the proportion of renewable vs. fossil fuel sources).

By optimizing code to reduce its runtime and resource consumption, developers can directly lower the value of E, which in turn reduces O and the overall SCI score. Eco-Coder is designed to make this optimization process tangible and data-driven by providing developers with the necessary metrics to understand and minimize the energy consumption (E) of their code.

### **2.3. The Developer's Dilemma: Lack of Actionable Tooling**

Despite the growing awareness of software's environmental impact and the existence of frameworks like the SCI, a significant barrier to the adoption of green software practices remains: the lack of integrated, developer-centric tooling. Developers are the primary actors who can implement energy-efficient code, but they are often working in an information vacuum regarding the environmental consequences of their design choices.  
A mature ecosystem of tools for measuring sustainability has emerged. Solutions like Cloud Carbon Footprint and the AWS Customer Carbon Footprint Tool provide excellent high-level views of cloud infrastructure emissions. Open-source libraries like CodeCarbon offer methods to estimate the carbon footprint of specific computational tasks. However, these tools typically provide data retroactively and at a coarse granularity (e.g., per-account or per-service). They do not provide feedback on the marginal carbon impact of a specific code change within a feature branch, which is the point at which a developer is most engaged and able to act on the information.  
Simultaneously, a powerful suite of tools for code analysis and performance profiling exists. Services like Amazon CodeGuru can automatically review code for quality issues, detect security vulnerabilities, and identify the most computationally expensive lines of code in a running application. These tools are invaluable for improving performance and reliability but do not inherently connect their findings to an environmental metric. A developer might be shown a performance bottleneck but is not given the context of its carbon cost.  
This reveals a critical integration gap. The problem is not a lack of data, but a failure to synthesize and contextualize it. The key to unlocking widespread adoption of green software engineering is to bridge the worlds of performance analysis and sustainability measurement. An effective solution must not invent a new measurement technique but rather create an intelligent intermediary—an agent—that can orchestrate these existing, powerful tools. This agent must be capable of invoking a performance profiler, feeding its output to a carbon estimator, and delivering a unified, actionable insight directly into the developer's native environment, such as a GitHub pull request. This is the precise, novel problem that Eco-Coder is designed to solve, establishing both the "Novelty of problem" and "Novelty of approach" required to excel in the hackathon's Creativity judging category.

## **Part III: Solution Overview: The Eco-Coder Agent Workflow**

### **3.1. User Journey: A Day in the Life of a Green Developer**

To understand the practical application and impact of Eco-Coder, it is best to walk through a typical end-to-end user journey. This narrative illustrates how the agent integrates seamlessly into the established workflows of a modern software development team, providing value without introducing friction.  
**Step 1: Code & Commit** A developer is working on a new feature for a Python-based application. They implement the required logic, which includes a computationally intensive data processing function. After completing their work, they follow standard procedure: they commit their code to a feature branch and open a pull request in their team's GitHub repository to merge the changes into the main branch.  
**Step 2: Agent Invocation** The creation of the pull request is the event that triggers the Eco-Coder agent. A pre-configured GitHub Action, listening for pull\_request events, fires a webhook. This webhook sends a payload containing the context of the pull request—including the repository name, pull request number, and commit hashes—to a secure Amazon API Gateway endpoint. The API Gateway, in turn, invokes an AWS Lambda function that serves as the entry point for the Eco-Coder agent workflow.  
**Step 3: Autonomous Analysis** The Eco-Coder agent, running on Amazon Bedrock, receives the pull request context. Its foundational LLM, guided by its core instruction prompt, begins its reasoning process. It understands its primary goal is to produce a "Green Code Report." To achieve this, it breaks the task down into a logical sequence of sub-tasks:

1. **Analyze Code Quality:** The agent decides it first needs to perform a static analysis of the new code. It invokes the CodeAnalysis tool, passing the repository and branch information. This tool programmatically initiates an Amazon CodeGuru Reviewer scan.  
2. **Profile Performance:** Simultaneously, the agent recognizes the need to understand the runtime impact. It invokes the PerformanceProfiling tool. This tool triggers a short, targeted performance profiling session using Amazon CodeGuru Profiler on a sandboxed environment running the new code.  
3. **Estimate Carbon Footprint:** Once the performance profiling is complete, the agent receives the key metrics (e.g., CPU time, memory usage). It reasons that it now has the necessary inputs to estimate the carbon impact. It invokes the CarbonEstimation tool, passing the performance data. This tool uses the CodeCarbon library to calculate the estimated CO2e emissions.  
4. **Synthesize and Report:** With all the necessary data collected—code quality recommendations, performance bottlenecks, and the carbon estimate—the agent's LLM performs its final and most critical task: synthesis. It combines all the information into a single, human-readable report. It may even generate specific code refactoring suggestions based on the identified issues. Finally, it invokes the RepositoryInteraction tool to post the complete report as a comment on the original GitHub pull request.

**Step 4: The "Green Code Report"** The developer and their team now see a new comment on their pull request from the Eco-Coder bot. This report provides a comprehensive overview of the sustainability and quality of the proposed changes. It includes:

* An overall **"Eco-Score"** (e.g., Grade C), providing an at-a-glance assessment.  
* The **Estimated CO2e Impact** of running the new code for a standardized workload, putting the environmental cost into concrete terms (e.g., "Equivalent to charging a smartphone 50 times").  
* A list of **Performance Bottlenecks** identified by CodeGuru Profiler, with direct links to the specific lines of code that are consuming the most CPU time.  
* A summary of **Code Quality & Security Issues** from CodeGuru Reviewer, such as potential resource leaks or security vulnerabilities.  
* **AI-Generated Refactoring Suggestions**, where the LLM provides concrete code snippets to address the identified inefficiencies, explicitly linking the performance improvement to a reduction in the carbon footprint.

The developer can now use this targeted feedback to refactor their code, push the improvements, and see an updated, more favorable report from Eco-Coder, completing a tight, efficient, and environmentally conscious feedback loop.

### **3.2. The Green Code Report: Anatomy of the Output**

The "Green Code Report" is the primary user interface of the Eco-Coder agent. Its design is critical for conveying complex information in a clear, concise, and actionable manner. The report will be formatted using Markdown for readability within the GitHub UI. The following is a detailed mock-up of its structure and content, which will be central to the project's demonstration video.  
**🤖 Eco-Coder Analysis Complete**  
Analysis of commit a1b2c3d is complete. Here is your Green Code Report:

### **🌿 Overall Eco-Score: C**

| Metric | Result | Details |
| :---- | :---- | :---- |
| **Est. Carbon Impact** | 🔴 **High** | 15.2 gCO2e per 1000 executions |
| **Performance** | 🟡 **Medium** | 2 bottlenecks identified |
| **Code Quality** | 🟢 **Good** | 1 minor issue found |

### **💨 Carbon Footprint Analysis**

Based on the performance profile, the changes in this pull request have an estimated carbon footprint of **15.2 grams of CO2 equivalent** per 1000 executions. This is equivalent to:

* Charging a smartphone \~3 times.  
* Driving an average gasoline car \~65 meters.

*This estimate is based on the us-east-1 AWS region's carbon intensity and the measured CPU/Memory consumption during profiling.*

### **⚙️ Performance Bottlenecks**

Amazon CodeGuru Profiler has identified the following performance hotspots:

1. **High CPU Usage in process\_data() function** (file: src/utils.py, line 42\)  
   * **Finding:** This function accounts for **78% of the total CPU time** during the profiling period. The nested loop structure appears to have a time complexity of O(n^2).  
   * **Recommendation:** Consider refactoring to use a more efficient algorithm or data structure, such as a hash map, to reduce the complexity to O(n).

### **📝 Code Quality Recommendations**

Amazon CodeGuru Reviewer has identified the following issue:

1. **Potential Resource Leak** (file: src/main.py, line 18\)  
   * **Finding:** The file object opened at line 18 is not properly closed in all code paths.  
   * **Recommendation:** Use a with statement to ensure the file handle is automatically closed.

### **✨ AI-Powered Refactoring Suggestion**

To address the primary performance bottleneck and reduce your carbon footprint, consider this refactoring of the process\_data() function:  
`# Inefficient Original Code`  
`def process_data(items):`  
    `processed =`  
    `for item in items:`  
        `for other_item in items:`  
            `if item.id == other_item.related_id:`  
                `processed.append(item)`  
    `return processed`

`# Suggested Refactoring`  
`def process_data(items):`  
    `related_ids = {item.related_id for item in items}`  
    `processed = [item for item in items if item.id in related_ids]`  
    `return processed`

*This change reduces the algorithmic complexity and is projected to decrease CPU time by over 70%, significantly improving your Eco-Score.*

## **Part IV: System Architecture and Technical Deep Dive**

### **4.1. High-Level Architecture Diagram**

The Eco-Coder system is designed as a robust, scalable, and secure serverless application on AWS. The architecture is event-driven, initiating its workflow from a webhook triggered by a GitHub pull request. The following diagram illustrates the logical flow of data and control between the components. This diagram is a mandatory submission deliverable and is foundational to demonstrating a well-architected solution that meets the "Technical Execution" judging criterion.  
**(A textual description of the architecture diagram follows, as a visual diagram cannot be rendered here.)**  
**Architecture Flow:**

1. **GitHub Repository:** A developer creates a pull request.  
2. **GitHub Actions (Webhook):** A pre-configured workflow detects the pull\_request event and sends a JSON payload to a defined endpoint.  
3. **Amazon API Gateway (REST API):** A secure, managed endpoint receives the webhook from GitHub. It validates the request and triggers the primary invocation handler.  
4. **AWS Lambda (Invocation Handler):** A lightweight Lambda function that receives the payload from API Gateway. Its sole purpose is to parse the pull request context (repo ARN, commit hash, etc.) and invoke the Amazon Bedrock Agent with this information.  
5. **Amazon Bedrock Agents (Orchestration Core):** This is the central brain of the operation. The agent receives the task and, using its underlying LLM, formulates a plan. It then invokes the necessary tools from its configured Action Groups to execute this plan.  
6. **Amazon Bedrock AgentCore Primitives:**  
   * **AgentCore Runtime:** The agent's execution logic is hosted within a secure, managed AgentCore Runtime environment, providing better isolation and scalability than a standard Lambda invocation.  
   * **AgentCore Gateway:** The Lambda functions that act as tools are exposed to the agent via an AgentCore Gateway. This provides a secure, discoverable, and managed API layer for the agent's capabilities.  
   * **AgentCore Memory:** (Optional but recommended for advanced implementation) A memory store is used to retain context about previous analyses on the same repository, allowing the agent to track sustainability trends over time.  
7. **Action Group Lambda Functions (Tools):** A set of specialized Lambda functions, each representing a "tool" the agent can use.  
   * lambda\_codeguru\_reviewer: Interacts with the Amazon CodeGuru Reviewer API.  
   * lambda\_codeguru\_profiler: Interacts with the Amazon CodeGuru Profiler API.  
   * lambda\_codecarbon: Executes the CodeCarbon library to perform CO2e calculations.  
   * lambda\_github\_poster: Interacts with the GitHub REST API to post comments back to the pull request.  
8. **External & AWS Service APIs:** The Lambda functions make calls to the respective service endpoints: Amazon CodeGuru, the GitHub API, and potentially a data source for the CodeCarbon library's regional intensity data.  
9. **Amazon Bedrock LLM (Synthesis):** After the tools return their data to the agent, the agent uses its underlying LLM to synthesize the results into the final, formatted "Green Code Report."  
10. **Return Path:** The agent invokes the lambda\_github\_poster tool, which sends the final report back to the GitHub API, causing it to appear as a comment on the pull request.

### **4.2. Orchestration Core: Amazon Bedrock Agents**

The intelligence and autonomy of Eco-Coder are powered by Amazon Bedrock Agents. This fully managed service enables the creation of agents that can understand natural language requests, break them down into logical steps, and interact with external systems through APIs to accomplish complex tasks.

#### **4.2.1. Agent Configuration**

The agent is configured within the Amazon Bedrock console or via the AWS SDK. Key configuration parameters include:

* **Agent Name:** Eco-Coder  
* **Agent Description:** "An AI agent that analyzes code in pull requests for performance, quality, and environmental impact, and provides a consolidated report to the developer."  
* **Foundation Model Selection:** The choice of the underlying LLM is critical to the agent's reasoning capabilities. **Anthropic's Claude 3 Sonnet on Bedrock** is selected for this project. This model offers a strong balance of performance, intelligence, and a large context window, making it well-suited for understanding complex code contexts and synthesizing diverse data sources into a coherent report.  
* **Instruction Prompt:** This is the most crucial piece of the configuration, as it defines the agent's persona, goal, constraints, and operational procedure. The prompt is carefully crafted to guide the LLM's reasoning process effectively.

**Instruction Prompt for Eco-Coder:**  
`You are Eco-Coder, an expert AI agent specializing in Green Software Engineering and DevOps best practices. Your primary directive is to analyze code changes submitted in a GitHub pull request and provide a comprehensive, actionable "Green Code Report."`

`Your goal is to help developers write more efficient, sustainable, and high-quality code.`

`You will be given the context of a pull request, including repository details and branch information. You must follow this exact sequence of actions:`

``1.  First, invoke the `CodeAnalysis` tool to initiate a static code review using Amazon CodeGuru Reviewer. This scan should run in the background.``  
``2.  Second, invoke the `PerformanceProfiling` tool to begin a runtime analysis of the code changes using Amazon CodeGuru Profiler.``  
``3.  Third, wait for the `PerformanceProfiling` tool to complete and return its results, which will include key metrics like CPU time.``  
``4.  Fourth, once you have the performance metrics, immediately invoke the `CarbonEstimation` tool, passing the metrics to it. This tool will return the estimated CO2e impact.``  
``5.  Fifth, wait for the `CodeAnalysis` tool to complete and return its findings.``  
`6.  Sixth, once you have the results from all three tools (Code Analysis, Performance Profiling, and Carbon Estimation), you must synthesize all the information into a single, well-formatted Markdown report. The report MUST include the following sections: 'Overall Eco-Score', 'Carbon Footprint Analysis', 'Performance Bottlenecks', and 'Code Quality Recommendations'.`  
``7.  Finally, invoke the `RepositoryInteraction` tool to post the complete, synthesized Markdown report as a comment on the original GitHub pull request.``

`Do not deviate from this plan. You must use the provided tools to gather all necessary information before generating the final report.`

#### **4.2.2. Orchestration Logic**

With the instruction prompt as its guide, the Bedrock Agent automates the orchestration process. When invoked with a user request (e.g., "Analyze pull request \#123 in repo my-app"), the agent's LLM interprets the request in the context of its instructions. It formulates an internal plan, which is visible in the agent's trace logs, that mirrors the steps outlined in the prompt. For example, the trace might show:

* **Observation:** User wants analysis of PR \#123.  
* **Thought:** My instructions say I need to run code analysis, performance profiling, and carbon estimation. I will start with code analysis and performance profiling.  
* **Action:** Invoke CodeAnalysis tool with repo=my-app, pr=123.  
* **Action:** Invoke PerformanceProfiling tool with repo=my-app, pr=123.  
* **Observation:** PerformanceProfiling returned cpu\_time: 1.2s.  
* **Thought:** Now I have the performance data, I can estimate the carbon footprint.  
* **Action:** Invoke CarbonEstimation tool with cpu\_time: 1.2s.  
* ...and so on.

This ability to reason, plan, and execute a sequence of tool calls is the core of the agent's functionality and a key requirement of the hackathon.

### **4.3. Tooling and Execution: Action Groups & AWS Lambda**

An agent's capabilities are defined by the tools it has access to. In Amazon Bedrock Agents, tools are organized into "Action Groups". Each action group defines a set of related functions the agent can perform, specified via an OpenAPI schema. The actual business logic for each tool is implemented in an AWS Lambda function.  
A key architectural decision for this project is to go beyond the basic Bedrock Agents service and leverage the more modular and powerful **Amazon Bedrock AgentCore** primitives, as strongly recommended by the hackathon rules. This demonstrates a deeper understanding of the AWS AI stack and results in a more robust and scalable solution. Instead of the agent invoking Lambda functions directly, the architecture will use **AgentCore Gateway** as a managed API layer for the tools. The gateway provides a stable, discoverable interface for the agent, simplifying tool management and enhancing security. The agent itself will be deployed to **AgentCore Runtime**, a purpose-built hosting environment that offers better performance and isolation for agentic workloads. This sophisticated design choice is a direct response to the "well-architected" component of the "Technical Execution" criterion.  
The following table provides the technical specifications for each tool available to the Eco-Coder agent.

| Action Group Name | AWS Lambda Function | Core APIs / Libraries Used | Input Parameters (JSON) | Output (JSON) |
| :---- | :---- | :---- | :---- | :---- |
| **CodeAnalysis** | lambda\_codeguru\_reviewer | boto3.client('codeguru-reviewer').create\_code\_review() boto3.client('codeguru-reviewer').describe\_code\_review() boto3.client('codeguru-reviewer').list\_recommendations() | {"repository\_arn": "string", "branch\_name": "string"} | JSON object containing a list of code quality and security recommendations, including file path, line numbers, and description. |
| **PerformanceProfiling** | lambda\_codeguru\_profiler | boto3.client('codeguru-profiler').configure\_agent() boto3.client('codeguru-profiler').get\_profile() boto3.client('codeguru-profiler').get\_recommendations() | {"profiling\_group\_name": "string", "start\_time": "iso8601", "end\_time": "iso8601"} | JSON object detailing performance bottlenecks, flame graph data, and key metrics like total CPU time and memory usage. |
| **CarbonEstimation** | lambda\_codecarbon | codecarbon Python library (EmissionsTracker) AWS Customer Carbon Footprint Tool API (for regional intensity) | {"cpu\_time\_seconds": "float", "ram\_usage\_mb": "float", "aws\_region": "string"} | JSON object with the estimated CO2e in grams and contextual equivalents (e.g., "equivalent to X smartphone charges"). |
| **RepositoryInteraction** | lambda\_github\_poster | requests (GitHub REST API) | {"pull\_request\_url": "string", "comment\_body": "string"} | JSON object confirming the status of the API call (e.g., {"status": "Success", "comment\_id": 12345}). |

### **4.4. Implementation Details: Programmatic API Interaction**

This section provides a more detailed look at the implementation logic within the key Lambda functions, demonstrating the feasibility and technical depth of the solution.

#### **4.4.1. CodeGuru Reviewer Integration (lambda\_codeguru\_reviewer)**

The process of programmatically interacting with Amazon CodeGuru Reviewer is asynchronous and requires a sequence of API calls managed by the Lambda function.

1. **Initiate Review:** The function is invoked by the agent with the repository\_arn and branch\_name. The first action is to call the create\_code\_review API endpoint. This call is configured for a RepositoryAnalysis type, which scans the entire tip of the specified branch.  
   `import boto3`  
   `client = boto3.client('codeguru-reviewer')`  
   `response = client.create_code_review(`  
       `Name=f"ecocoder-review-{pr_number}",`  
       `RepositoryAssociationArn=repository_arn,`  
       `Type={`  
           `'RepositoryAnalysis': {`  
               `'RepositoryHead': {`  
                   `'BranchName': branch_name`  
               `}`  
           `}`  
       `}`  
   `)`  
   `code_review_arn = response`

2. **Poll for Completion:** The code review process can take several minutes. The Lambda function cannot wait this long. Therefore, the create\_code\_review call will trigger a workflow (e.g., using AWS Step Functions) that polls the status of the review. A separate poller function will periodically call describe\_code\_review with the code\_review\_arn. It will check the State field in the response. The polling continues until the state is Completed or Failed.  
3. **Fetch Recommendations:** Once the review is complete, the final step is to call list\_recommendations, passing the code\_review\_arn. This returns a paginated list of all findings. The Lambda function formats these findings into a structured JSON object and returns it to the Bedrock Agent.

#### **4.4.2. CodeCarbon Integration (lambda\_codecarbon)**

The lambda\_codecarbon function is responsible for translating performance metrics into a carbon estimate. It leverages the open-source codecarbon Python library.

1. **Receive Inputs:** The function is invoked by the agent with the outputs from the lambda\_codeguru\_profiler function, specifically cpu\_time\_seconds, ram\_usage\_mb, and the aws\_region.  
2. **Offline Calculation:** The codecarbon library can be run in an "offline" mode where energy consumption values are provided directly, rather than measured from hardware sensors. The function will also need the carbon intensity for the specified AWS region. This data can be pre-loaded into the Lambda layer or fetched from a public API.  
3. **Execute Estimation:** The core logic involves instantiating the EmissionsTracker and providing it with the known energy consumption and carbon intensity to calculate the final CO2e value. A simplified representation of the logic is as follows:  
   `from codecarbon import EmissionsTracker`

   `def estimate_emissions(cpu_time_seconds, ram_usage_mb, aws_region):`  
       `# Fetch carbon intensity for the given AWS region`  
       `carbon_intensity_g_per_kwh = get_carbon_intensity(aws_region)`

       `# Assume average power draw for CPU and RAM (can be refined)`  
       `CPU_POWER_WATT = 45`  
       `RAM_POWER_WATT = 5`

       `# Calculate energy consumption in kWh`  
       `cpu_energy_kwh = (cpu_time_seconds * CPU_POWER_WATT) / (3600 * 1000)`  
       `#... similar calculation for RAM...`  
       `total_energy_kwh = cpu_energy_kwh # + ram_energy_kwh`

       `# Calculate CO2 equivalent in grams`  
       `co2_grams = total_energy_kwh * carbon_intensity_g_per_kwh`

       `return co2_grams`  
   This function provides the core calculation, which is then formatted and returned to the Bedrock Agent.

## **Part V: Strategic Alignment with Hackathon Judging Criteria**

A successful hackathon submission requires not only a strong technical implementation but also a clear and compelling alignment with the judging criteria. The Eco-Coder project has been meticulously designed from the ground up to excel in every category defined by the AWS AI Agent Global Hackathon rules. This section explicitly maps the project's features and design choices to each criterion, providing a clear justification for why Eco-Coder is a winning solution.  
One of the project's most powerful attributes is its potential for a cascading, positive impact that extends far beyond its immediate function. The direct, measurable impact of the tool is the reduction in CO2 emissions from a single, optimized pull request. While valuable, this is a localized effect. The true, transformative value lies in the tool's ability to act as an educational and cultural catalyst. When developers are consistently presented with a tangible metric for the environmental cost of their work, their behavior and mindset begin to shift. They learn to recognize inefficient patterns not just as performance issues, but as sustainability issues. This educational feedback loop creates a generation of carbon-aware developers who are more likely to write efficient code by default, even on projects where the tool is not deployed. This, in turn, fosters a cultural shift within engineering organizations, where sustainability becomes a core tenet of software quality, influencing architectural decisions, hiring practices, and the very definition of "good code." This "impact multiplier" effect elevates the project's value from a simple utility to a powerful agent for systemic change in the software industry.  
The following scorecard provides a detailed breakdown of the project's alignment with the official judging criteria.

| Criterion | Weight | Eco-Coder's Alignment and Justification |
| :---- | :---- | :---- |
| **Technical Execution** | 50% | \- **Well-Architected:** The project utilizes a modern, serverless, and event-driven architecture based on Amazon API Gateway, AWS Lambda, and Amazon Bedrock. This design is inherently scalable, resilient, and cost-effective. Crucially, the architecture demonstrates advanced knowledge of the AWS AI stack by explicitly leveraging **Amazon Bedrock AgentCore** primitives (Runtime, Gateway, Memory), directly addressing the hackathon's strong recommendation and showcasing a sophisticated, production-ready design. \- **Reproducible:** All infrastructure will be defined as code using the AWS Cloud Development Kit (CDK) or AWS CloudFormation templates. The public GitHub repository, a mandatory deliverable, will contain all source code for the Lambda functions, the infrastructure-as-code templates, and a detailed README.md with step-by-step deployment instructions, ensuring that the judges can easily reproduce the entire solution. \- **Must use required technology:** The solution is fundamentally built on **Amazon Bedrock Agents**, satisfying the primary requirement. It uses an **LLM hosted on Amazon Bedrock** (Anthropic Claude 3 Sonnet) for its reasoning core. The agent is designed to **integrate with multiple APIs and external tools** (Amazon CodeGuru, CodeCarbon, GitHub API), fulfilling another core requirement. The project thus meets all three mandatory technical conditions outlined in the hackathon rules. |
| **Potential Value/Impact** | 20% | \- **Solves a Real-World Problem:** Eco-Coder addresses the urgent and globally significant problem of the software industry's growing carbon footprint. This is a well-documented issue with clear environmental and economic consequences, making the solution highly relevant and impactful. \- **Measurable Impact:** The agent provides quantifiable CO2e estimates for every code change, allowing for the direct measurement of sustainability improvements. The project's true value is amplified by the "impact multiplier" effect described above; by educating developers and embedding sustainability into the development culture, it creates a long-term, systemic reduction in carbon emissions that far exceeds the impact of any single code fix. |
| **Creativity** | 10% | \- **Novelty of Problem:** The project applies the power of AI agents to the novel and emerging domain of Green Software Engineering. While AI has been used for code generation and analysis, its application as an autonomous agent for sustainability feedback within the CI/CD pipeline is a new and innovative concept. \- **Novelty of Approach:** The core creative leap of Eco-Coder is the synthesis of data from disparate, specialized domains—static code analysis, dynamic performance profiling, and environmental science (carbon intensity data). The agent does not just present these data points; its LLM-powered reasoning core intelligently combines them to create a holistic, contextualized, and actionable report that is more valuable than the sum of its parts. This unique application of agentic AI to bridge the developer workflow gap is the project's key innovation. |
| **Functionality** | 10% | \- **Working Agent:** The project will be deployed and fully functional. The submission will include a URL to the deployed project's entry point (the API Gateway endpoint) and clear instructions for judges to configure a webhook on a test repository to see the agent in action. The agent will demonstrate the complete, end-to-end workflow as described in the user journey. \- **Scalable:** The choice of a serverless architecture ensures that the solution is inherently scalable. AWS Lambda, API Gateway, and Amazon Bedrock are all managed services that automatically scale to handle fluctuating loads, making the solution capable of supporting anything from a single repository to an enterprise-wide deployment with thousands of developers. |
| **Demo Presentation** | 10% | \- **End-to-End Workflow:** The mandatory 3-minute demonstration video will be carefully storyboarded to clearly and concisely showcase the entire agentic workflow, from the moment a pull request is created to the final, detailed report being posted by the agent. This will provide a compelling and easy-to-understand narrative for the judges. \- **Clarity and Quality:** The presentation plan, detailed in the following section, ensures a professional, polished, and persuasive demonstration. The video will use clear on-screen text, smooth transitions, and a focused voiceover to highlight the agent's intelligence, its seamless integration, and its profound impact, maximizing the score for this criterion. |

## **Part VI: Demonstration and Presentation Plan**

### **6.1. Video Storyboard (3-Minute Demo)**

The demonstration video is a critical component of the submission, serving as the primary vehicle for conveying the project's functionality and vision. The following storyboard outlines a compelling 3-minute narrative designed to be clear, impactful, and aligned with the judging criteria.  
**Total Runtime:** 2 minutes, 55 seconds

| Time | Visuals | Audio (Voiceover) |
| :---- | :---- | :---- |
| **0:00 \- 0:25** | **(The Problem)** Fast-paced montage: shots of massive data center server racks, spinning fans, glowing LEDs. Overlay text: "Data centers consume \>1% of global electricity." Final shot of a world map with energy consumption hotspots. | "Our digital world runs on code. But this code runs on hardware that consumes massive amounts of energy, contributing significantly to global carbon emissions. Every line of inefficient code has a real environmental cost." |
| **0:25 \- 0:45** | **(The Solution)** Clean, animated graphic of the Eco-Coder logo appearing on screen. The logo is a stylized leaf integrated with code brackets \<\>. Transition to a shot of the GitHub pull request interface. | "But what if developers could see this cost before their code ever reaches production? Introducing Eco-Coder: an autonomous AI agent for sustainable software development. It brings environmental insights directly into your existing workflow." |
| **0:45 \- 1:15** | **(Live Demo: The Trigger)** Screen recording. A developer is shown in a code editor (VS Code) writing a Python function with an obvious O(n^2) nested loop. They commit the code and create a new pull request on GitHub. | "Here, a developer submits a new feature. The moment the pull request is created, Eco-Coder is automatically triggered." |
| **1:15 \- 1:45** | **(Live Demo: The Analysis)** The GitHub pull request page is shown. A comment from the "Eco-Coder" bot appears: "🤖 Analysis in progress..." The screen then shows a quick, stylized animation of the AWS architecture diagram, with icons for Bedrock, CodeGuru, and Lambda pulsing. | "Behind the scenes, our agent, powered by Amazon Bedrock, orchestrates a deep analysis. It uses Amazon CodeGuru to profile the code's performance and a custom tool to calculate the resulting carbon footprint." |
| **1:45 \- 2:20** | **(Live Demo: The Report)** Back on the GitHub page, the "Analysis in progress" comment is replaced by the full "Green Code Report." The mouse cursor scrolls through the report, highlighting the 'C' Eco-Score, the 15.2 gCO2e estimate, and the specific performance bottleneck in the nested loop. | "In minutes, the agent delivers its findings directly in the pull request. It provides a clear Eco-Score, a tangible carbon estimate, and pinpoints the exact lines of inefficient code." |
| **2:20 \- 2:40** | **(Live Demo: The Fix)** The cursor highlights the AI-generated refactoring suggestion in the report. The developer copies the suggested efficient code, pastes it into their editor, commits the change, and pushes the update. A few moments later, the Eco-Coder comment updates with a new "Eco-Score: A" and a much lower CO2e value. | "Most importantly, it provides an AI-powered suggestion to fix the issue. The developer applies the fix, pushes the update, and immediately sees the positive impact on their Eco-Score. This is the feedback loop for green software." |
| **2:40 \- 2:55** | **(The Vision)** Final shot of the Eco-Coder logo over a backdrop of green, abstract data visualizations. | "Eco-Coder is more than a tool; it's an agent of change. By empowering developers with actionable data, we can build a more sustainable digital future. One pull request at a time." |

### **6.2. Key Talking Points for Presentation**

This script outline provides the core narrative for any live presentation or for the voiceover script, ensuring all key strategic points are communicated effectively.

1. **Introduction (The "Why"):**  
   * Start with the problem: Software's "silent" carbon footprint is a massive, unsolved problem.  
   * Introduce the core idea: We're making this invisible cost *visible* to the people who can fix it—developers.  
   * State the project name and its one-line pitch: "Eco-Coder, an AI agent that integrates sustainability analysis into the CI/CD pipeline."  
2. **The Solution (The "What"):**  
   * Briefly walk through the user journey shown in the video: PR created \-\> Agent triggered \-\> Analysis \-\> Report delivered.  
   * Emphasize the key output: The "Green Code Report." Highlight its components: Eco-Score, CO2e estimate, performance bottlenecks, and AI-powered refactoring suggestions.  
   * Stress the importance of the feedback loop: The agent provides actionable data *where* developers work and *when* it matters most.  
3. **Technical Excellence (The "How"):**  
   * Mention the core technology: "This is all orchestrated by an autonomous agent built on **Amazon Bedrock Agents**."  
   * Highlight the sophisticated architecture: "We've designed a well-architected, serverless solution that leverages **Amazon Bedrock AgentCore** primitives for scalability and security, as recommended by the hackathon."  
   * Name the key integrations: "The agent intelligently combines outputs from **Amazon CodeGuru** for performance profiling and the **CodeCarbon** library for emissions estimation." This showcases fulfillment of the technical requirements.  
4. **Impact & Vision (The "Why It Matters"):**  
   * Reiterate the value proposition: This isn't just about fixing one inefficient function.  
   * Introduce the "Impact Multiplier" concept: "By providing this constant feedback, Eco-Coder educates developers and fosters a culture of sustainability, creating a long-term, systemic shift towards green software engineering."  
   * Close with a strong, memorable vision statement: "Eco-Coder empowers the world's developers to become agents of environmental change, helping to build the greener, more efficient digital infrastructure of tomorrow."

## **Part VII: Roadmap for Future Development**

The Eco-Coder project, as proposed for this hackathon, establishes a powerful and functional foundation. However, its potential extends far beyond the initial implementation. This roadmap outlines a series of short-term enhancements and a long-term vision for evolving Eco-Coder into a comprehensive platform for enterprise-wide software sustainability.

### **7.1. Short-Term Enhancements**

These features represent the next logical steps in the project's development, building directly upon the core architecture.

* **Automated Refactoring with One-Click Apply:** The current agent suggests refactoring solutions. The next evolution is to make these suggestions directly actionable. By integrating with a code generation model like **Amazon CodeWhisperer** , the agent could present its suggested code fix with a "Apply Fix" button directly in the pull request comment. Clicking this button would trigger another agent action to automatically create a new commit with the refactored code, dramatically reducing the friction for developers to implement sustainable improvements.  
* **Expanded Language and Framework Support:** The initial implementation focuses on Python and Java, the primary languages supported by Amazon CodeGuru. A high-priority next step is to expand support to other popular languages (e.g., JavaScript,.NET) as they become available in CodeGuru and other profiling tools. This would significantly broaden the addressable market and impact of the agent.  
* **Real-Time IDE Integration:** While feedback at the pull request stage is highly valuable, the ultimate "shift-left" approach is to provide feedback as the developer is writing the code. A VS Code or JetBrains IDE extension could be developed that communicates with a backend Eco-Coder service. This extension would perform lightweight, real-time analysis on code blocks as they are being written, highlighting potentially energy-intensive patterns and suggesting alternatives on the fly, preventing inefficient code from ever being committed.

### **7.2. Long-Term Vision**

The long-term vision for Eco-Coder is to transform it from a developer tool into an enterprise sustainability intelligence platform.

* **Organizational Sustainability Dashboard:** The data generated by the agent for each pull request is incredibly valuable in aggregate. A web-based dashboard could be developed that connects to the Eco-Coder data store (e.g., Amazon DynamoDB). This dashboard would provide C-level executives, engineering managers, and sustainability officers with a holistic view of the organization's software carbon footprint. It could track trends over time, identify the "least green" repositories or teams, and gamify sustainability by creating leaderboards, providing a powerful tool for driving top-down sustainability initiatives.  
* **Hardware and Infrastructure Efficiency Recommendations:** The current agent focuses on Operational Emissions (O) by optimizing code. A more advanced version could also help optimize for Embodied Emissions (M) by influencing infrastructure choices. By analyzing the performance profile of an application, a future agent could recommend more energy-efficient cloud resources. For example, it could suggest migrating a workload to a newer, more efficient AWS instance type (e.g., Graviton processors) or advise that a particular service is a good candidate for a serverless architecture like AWS Lambda, which can be more hardware-efficient for intermittent workloads.  
* **Open Source and Community Contribution:** To maximize its impact and accelerate innovation, the core logic of the Eco-Coder agent—specifically its tool implementations and the logic for synthesizing reports—could be released as an open-source project. This would align with the collaborative spirit of the green software community and leverage the collective expertise of developers worldwide. By contributing to the ecosystem of open-source green software tools, Eco-Coder can become a foundational component that others can build upon, fostering wider adoption and creating a global standard for sustainable code analysis. This would cement the project's legacy as a true "agent of change" for the entire software industry.

#### **Works cited**

1\. AI Agents for Sustainability: Reducing Waste and Environmental Impact \- Akira AI, https://www.akira.ai/blog/ai-agents-for-sustainability-and-waste-reduction 2\. Cloud Carbon Footprint \- An open source tool to measure and analyze cloud carbon emissions, https://www.cloudcarbonfootprint.org/ 3\. Customer Carbon Footprint Tool \- AWS, https://aws.amazon.com/aws-cost-management/aws-customer-carbon-footprint-tool/ 4\. Optimize Code Performance – Amazon CodeGuru Profiler Features \- AWS, https://aws.amazon.com/codeguru/profiler/features/ 5\. Amazon CodeGuru Security \- AWS, https://aws.amazon.com/codeguru/ 6\. CodeCarbon.io, https://codecarbon.io/ 7\. AI Agents for Sustainable Enterprise: A Leader's Guide \- GreenMetrica, https://www.greenmetrica.com/ai-agents 8\. Chapter 8 \- AI Agents and Sustainable Development Goals: Bridging the Gap Through Innovation \- Research Highlights & Events, https://research.sbs.edu/sbsrm/SBSRM01\_Chapter\_08.pdf 9\. Top 10 Sustainability AI Applications & Examples \- Research AIMultiple, https://research.aimultiple.com/sustainability-ai/ 10\. Software Carbon Intensity (SCI) Specification, https://sci.greensoftware.foundation/ 11\. Amazon CodeGuru Documentation, https://docs.aws.amazon.com/codeguru/ 12\. Top AI Agents for Software Development in 2025 \- TopDevelopers.co, https://www.topdevelopers.co/directory/research/ai-agents-for-software-development/ 13\. What are AI agents? \- GitHub, https://github.com/resources/articles/ai/what-are-ai-agents 14\. AI Agents – Amazon Bedrock Agents – AWS, https://aws.amazon.com/bedrock/agents/ 15\. Amazon Bedrock Agents \- AWS Prescriptive Guidance, https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-frameworks/bedrock-agents.html 16\. Get started with Amazon Bedrock \- AWS Documentation, https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html 17\. Amazon Bedrock AgentCore Documentation \- AWS Documentation, https://docs.aws.amazon.com/bedrock-agentcore/ 18\. Getting started with Amazon Bedrock AgentCore \- AWS, https://aws.amazon.com/bedrock/agentcore/getting-started/ 19\. Actions \- Amazon CodeGuru Reviewer \- AWS Documentation, https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API\_Operations.html 20\. create-code-review — AWS CLI 2.31.15 Command Reference, https://docs.aws.amazon.com/cli/latest/reference/codeguru-reviewer/create-code-review.html 21\. CodeGuruReviewer — Boto3 Docs 1.17.5 documentation \- AWS, https://boto3.amazonaws.com/v1/documentation/api/1.17.5/reference/services/codeguru-reviewer.html 22\. CreateCodeReview \- Amazon CodeGuru Reviewer \- AWS Documentation, https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API\_CreateCodeReview.html 23\. ListRecommendations \- Amazon CodeGuru Reviewer \- AWS Documentation, https://docs.aws.amazon.com/codeguru/latest/reviewer-api/API\_ListRecommendations.html 24\. list-recommendations — AWS CLI 2.31.3 Command Reference, https://docs.aws.amazon.com/cli/latest/reference/codeguru-reviewer/list-recommendations.html 25\. CodeCarbon API — CodeCarbon 3.0.5 documentation \- GitHub Pages, https://mlco2.github.io/codecarbon/api.html 26\. CodeCarbon 3.0.7 documentation \- GitHub Pages, https://mlco2.github.io/codecarbon/ 27\. You can't reduce what you can't measure \- Getting started with CodeCarbon \- Pebble, https://www.gopebble.com/pebble-academy/using-codecarbon-to-track-carbon 28\. Amazon CodeWhisperer Documentation \- AWS, https://aws.amazon.com/documentation-overview/codewhisperer/ 29\. Amazon CodeWhisperer Documentation, https://docs.aws.amazon.com/codewhisperer/ 30\. Amazon CodeGuru Reviewer \- AWS Documentation, https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/welcome.html 31\. Google Open Source, https://opensource.google/ 32\. Guide: Top 7 "Open Source" Sustainability Tools \- Suston Magazine, https://sustonmagazine.com/open-source-esg-outdoor-transparency/ 33\. Green-Software-Foundation/awesome-green-software \- GitHub, https://github.com/Green-Software-Foundation/awesome-green-software 34\. The 10 best tools to green your software \- The GitHub Blog, https://github.blog/open-source/social-impact/the-10-best-tools-to-green-your-software/