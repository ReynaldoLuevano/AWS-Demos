"""
bedrock_construct.py
Amazon Bedrock — Knowledge Base, Agent 1 (Evaluator), Agent 2 (Diagram Generator),
                 and Supervisor Agent with multi-agent collaboration.

Requires:
    bedrock_agent_role    (iam.Role)       — Shared execution role for all agents
    oss_collection_arn    (str)            — OpenSearch Serverless collection ARN
    kb_bucket             (s3.Bucket)      — S3 bucket with best practices documents
    reports_bucket        (s3.Bucket)      — S3 bucket for output reports & diagrams
    reviews_table         (dynamodb.Table) — DynamoDB table for review state
    inventory_scanner_fn  (lambda.Function)— Action group executor for Agent 1
    drawio_generator_fn   (lambda.Function)— Action group executor for Agent 2
    bedrock_orch_fn       (lambda.Function)— Lambda that invokes the Supervisor Agent
    review_queue          (sqs.Queue)      — Queue that triggers bedrock_orch_fn

Exposes:
    knowledge_base        (CfnKnowledgeBase)
    evaluator_agent       (CfnAgent)
    diagram_agent         (CfnAgent)
    supervisor_agent      (CfnAgent)
    supervisor_alias      (CfnAgentAlias)
"""

import aws_cdk as cdk
import aws_cdk.aws_bedrock as bedrock
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_sqs as sqs
from constructs import Construct

# Claude 3.5 Sonnet v2 — foundation model used by all agents
FOUNDATION_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class BedrockConstruct(Construct):
    """Creates Bedrock Knowledge Base, two specialist agents, and a Supervisor Agent."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bedrock_agent_role: iam.Role,
        oss_collection_arn: str,
        kb_bucket: s3.Bucket,
        reports_bucket: s3.Bucket,
        reviews_table: dynamodb.Table,
        inventory_scanner_fn: _lambda.Function,
        drawio_generator_fn: _lambda.Function,
        bedrock_orch_fn: _lambda.Function,
        review_queue: sqs.Queue,
    ) -> None:
        super().__init__(scope, construct_id)

        stack = cdk.Stack.of(self)
        model_arn = (
            f"arn:aws:bedrock:{stack.region}::foundation-model/{FOUNDATION_MODEL}"
        )

        # ── Knowledge Base ─────────────────────────────────────────────────
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "WARKnowledgeBase",
            name="war-best-practices-kb",
            description=(
                "Knowledge base with AWS best practices, "
                "Well-Architected whitepapers and service guides"
            ),
            role_arn=bedrock_agent_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=(
                        f"arn:aws:bedrock:{stack.region}::foundation-model/"
                        "amazon.titan-embed-text-v2:0"
                    )
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=oss_collection_arn,
                    vector_index_name="war-best-practices-index",
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        vector_field="embedding",
                        text_field="text",
                        metadata_field="metadata",
                    ),
                ),
            ),
        )

        # S3 data source for the Knowledge Base
        self.kb_data_source = bedrock.CfnDataSource(
            self,
            "KBDataSource",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            name="war-kb-s3-datasource",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=kb_bucket.bucket_arn,
                    inclusion_prefixes=["whitepapers/", "best-practices/", "service-guides/"],
                ),
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="SEMANTIC",
                    semantic_chunking_configuration=bedrock.CfnDataSource.SemanticChunkingConfigurationProperty(
                        max_tokens=300,
                        buffer_size=0,
                        breakpoint_percentile_threshold=95,
                    ),
                )
            ),
        )

        # ── Agent 1 — Best Practices Evaluator ────────────────────────────
        self.evaluator_agent = bedrock.CfnAgent(
            self,
            "EvaluatorAgent",
            agent_name="war-best-practices-evaluator",
            description=(
                "Evaluates AWS resource configurations against Well-Architected "
                "best practices using the Knowledge Base and WAT questions"
            ),
            foundation_model=model_arn,
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            instruction=_EVALUATOR_INSTRUCTION,
            knowledge_base_associations=[
                bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
                    description=(
                        "AWS Well-Architected best practices, "
                        "whitepapers and service documentation"
                    ),
                )
            ],
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="InventoryActions",
                    description="Retrieve resource inventory and configuration from DynamoDB",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=inventory_scanner_fn.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="getResourcesByTag",
                                description="Retrieve all AWS resources tagged with a specific application tag",
                                parameters={
                                    "appTag": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="The application tag value to filter resources",
                                        required=True,
                                    )
                                },
                            ),
                            bedrock.CfnAgent.FunctionProperty(
                                name="getResourceConfig",
                                description="Retrieve the detailed configuration of a specific resource",
                                parameters={
                                    "resourceArn": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="The ARN of the resource to inspect",
                                        required=True,
                                    )
                                },
                            ),
                        ]
                    ),
                )
            ],
        )

        self.evaluator_agent_alias = bedrock.CfnAgentAlias(
            self,
            "EvaluatorAgentAlias",
            agent_id=self.evaluator_agent.attr_agent_id,
            agent_alias_name="live",
            description="Production alias for Evaluator Agent",
        )

        # ── Agent 2 — Architecture Diagram Generator ───────────────────────
        self.diagram_agent = bedrock.CfnAgent(
            self,
            "DiagramGeneratorAgent",
            agent_name="war-diagram-generator",
            description=(
                "Generates draw.io architecture diagrams from "
                "resource inventory and configurations"
            ),
            foundation_model=model_arn,
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            instruction=_DIAGRAM_GENERATOR_INSTRUCTION,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="DiagramGeneratorActions",
                    description="Generate and save draw.io diagram files to S3",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=drawio_generator_fn.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="generateAndSaveDiagram",
                                description="Generate a draw.io XML diagram and save it to S3",
                                parameters={
                                    "drawioXml": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="The complete draw.io XML content for the diagram",
                                        required=True,
                                    ),
                                    "diagramName": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Name for the diagram file (without extension)",
                                        required=True,
                                    ),
                                    "reviewId": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="The review ID to associate the diagram with",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                )
            ],
        )

        self.diagram_agent_alias = bedrock.CfnAgentAlias(
            self,
            "DiagramGeneratorAgentAlias",
            agent_id=self.diagram_agent.attr_agent_id,
            agent_alias_name="live",
            description="Production alias for Diagram Generator Agent",
        )

        # ── Supervisor Agent ───────────────────────────────────────────────
        self.supervisor_agent = bedrock.CfnAgent(
            self,
            "SupervisorAgent",
            agent_name="war-supervisor",
            description=(
                "Orchestrates the Well-Architected review process by coordinating "
                "Agent 1 (evaluator) and Agent 2 (diagram generator)"
            ),
            foundation_model=model_arn,
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            instruction=_SUPERVISOR_INSTRUCTION,
            agent_collaboration="SUPERVISOR",
            agent_collaborators=[
                bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=self.evaluator_agent_alias.attr_agent_alias_arn
                    ),
                    collaboration_instruction=(
                        "Evaluate the AWS resource configurations against Well-Architected "
                        "best practices and return a detailed findings report"
                    ),
                    collaborator_name="EvaluatorAgent",
                    relay_conversation_history="TO_COLLABORATOR",
                ),
                bedrock.CfnAgent.AgentCollaboratorProperty(
                    agent_descriptor=bedrock.CfnAgent.AgentDescriptorProperty(
                        alias_arn=self.diagram_agent_alias.attr_agent_alias_arn
                    ),
                    collaboration_instruction=(
                        "Generate a draw.io architecture diagram based on the "
                        "discovered resources and save it to S3"
                    ),
                    collaborator_name="DiagramGeneratorAgent",
                    relay_conversation_history="TO_COLLABORATOR",
                ),
            ],
        )

        self.supervisor_alias = bedrock.CfnAgentAlias(
            self,
            "SupervisorAgentAlias",
            agent_id=self.supervisor_agent.attr_agent_id,
            agent_alias_name="live",
            description="Production alias for Supervisor Agent",
        )

        # Expose Supervisor Agent ID to the Bedrock orchestrator Lambda
        bedrock_orch_fn.add_environment(
            "SUPERVISOR_AGENT_ID", self.supervisor_agent.attr_agent_id
        )
        bedrock_orch_fn.add_environment(
            "SUPERVISOR_AGENT_ALIAS_ID", self.supervisor_alias.attr_agent_alias_id
        )


# ── Agent instruction strings (kept outside the class for readability) ─────────

_EVALUATOR_INSTRUCTION = """\
You are an expert AWS Well-Architected Framework reviewer.
Your job is to evaluate AWS resource configurations against best practices for a given lens.

When evaluating:
1. Retrieve relevant best practices from the Knowledge Base
2. Compare the actual resource configurations provided against those best practices
3. For each Well-Architected question provided, determine if the workload follows the best practice
4. Identify risks: HIGH, MEDIUM, LOW
5. Generate actionable recommendations for each finding
6. Score each pillar (0-100) based on compliance

Always structure your output as a JSON report with: summary, pillar_scores, findings[], recommendations[]
"""

_DIAGRAM_GENERATOR_INSTRUCTION = """\
You are an expert AWS Solutions Architect specialising in creating architecture diagrams.
Your job is to generate draw.io (XML) diagrams that accurately represent AWS architectures.

When generating diagrams:
1. Use official AWS service icons from the mxgraph.aws4 shape library
2. Group resources by VPC, subnet, availability zone, or logical function
3. Show data flow with labelled arrows indicating protocol or purpose
4. Use colour-coded groups: orange for frontend, blue for compute, green for data, purple for AI/ML
5. Include a legend and title
6. Generate valid draw.io XML that can be directly imported into app.diagrams.net

Always call the generateAndSaveDiagram action with the complete XML content.
"""

_SUPERVISOR_INSTRUCTION = """\
You are the supervisor for an automated Well-Architected review.
When you receive a review request with an appTag and lensAlias:

1. INVENTORY: Retrieve all resources tagged with the appTag
2. WAT QUESTIONS: The questions for the lens have been provided to you
3. DELEGATE EVALUATION: Call the EvaluatorAgent to evaluate resources against WAT questions
4. DELEGATE DIAGRAM: Call the DiagramGeneratorAgent to generate an architecture diagram
5. COMPILE REPORT: Combine findings from both agents into a final report
6. RETURN: A JSON object with: evaluation_report, diagram_s3_url, summary, pillar_scores

Be thorough and systematic. Always complete all steps before returning the final result.
"""
