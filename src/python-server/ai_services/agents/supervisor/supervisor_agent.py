from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from langchain.google_genai import ChatGoogleGenerativeAI
from langchain.anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
import os
import sys
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from agents.supervisor.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from agents.complex_task_agent.complex_excel_request_agent_graph import ComplexExcelRequestAgent
from agents.prebuilt_agent import PrebuiltAgent

gemini_api_key = os.getenv("GEMINI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
supervisor_model = ChatAnthropic(model_name="claude-3-7-sonnet-latest", api_key=anthropic_api_key)
simple_request_model_name = "claude-3-7-latest"
simple_request_agent = PrebuiltAgent().with_model(simple_request_model_name)
complex_request_model_name = "gemini-2.5-pro"
complex_request_agent = ComplexExcelRequestAgent().with_model(complex_request_model_name)

supervisor_agent = create_supervisor(
    [simple_request_agent, complex_request_agent],
    model=supervisor_model,
    prompt=SUPERVISOR_SYSTEM_PROMPT,
    output_mode="full_history",
    store=InMemoryStore(),
    checkpointer=InMemorySaver()
)

# Compile and run
agent_system = supervisor_agent.compile()
result = agent_system.invoke({
    "messages": [
        {
            "role": "user",
            "content": "what's the combined headcount of the FAANG companies in 2024?"
        }
    ]
})