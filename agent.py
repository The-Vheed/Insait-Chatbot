import os
import csv
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents import AgentExecutor
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_openai import ChatOpenAI

load_dotenv("./env")


class GetOrderStatusInput(BaseModel):
    order_id: str = Field(description="The ID of the order")


@tool("GetOrderStatus", args_schema=GetOrderStatusInput, return_direct=False)
def GetOrderStatus(order_id):
    """
    Get the status of the user's order with the order_id
    """

    # Simulate function to get the status of an order using the ID
    return "Pending"


@tool("GetAllReturnPolices", return_direct=False)
def GetAllReturnPolices() -> str:
    """
    Get all the Return Policies to help with answering related queries, e.g: Return Period, Return Method, etc
    """
    return """
    Q: What is the return policy for items purchased at our store?
    A: You can return most items within 30 days of purchase for a full refund or
    exchange. Items must be in their original condition, with all tags and
    packaging intact. Please bring your receipt or proof of purchase when
    returning items.

    Q: Are there any items that cannot be returned under this policy?
    A: Yes, certain items such as clearance merchandise, perishable goods, and
    personal care items are non-returnable. Please check the product description
    or ask a store associate for more details.

    Q: How will I receive my refund?
    A: Refunds will be issued to the original form of payment. If you paid by
    credit card, the refund will be credited to your card. If you paid by cash or
    check, you will receive a cash refund.
    """


class ExportUserDataInput(BaseModel):
    full_name: str = Field(description="Full name of the user")
    email: str = Field(description="Email of the user")
    phone: str = Field(description="Phone number of the user")


@tool("ExportUserData", args_schema=ExportUserDataInput, return_direct=False)
def ExportUserData(full_name, email, phone) -> str:
    """
    Exports the user data to a CSV file to enable hand-over to a human correspondent
    """
    filename = "user_data.csv"
    file_exists = os.path.exists(filename)
    try:
        with open(
            filename, "a", newline="", encoding="utf-8"
        ) as csvfile:  # utf-8 encoding for special characters
            fieldnames = ["full_name", "email", "phone"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()  # Write header only if the file is new

            writer.writerow({"full_name": full_name, "email": email, "phone": phone})
        return "Contact information saved successfully."
    except Exception as e:
        return f"An error occurred while saving contact information: {e}"


llm = ChatOpenAI(temperature=0.1, model="gpt-4o")

tools = [GetOrderStatus, GetAllReturnPolices, ExportUserData]
# pkl.dump(tools, open('tools.pkl', 'wb'))

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a very powerful conversational chatbot that asks only one question at a time until you have all the necessary data to compelete a task.\n\
            You never generate fake data for any reason.\n\
            Try as much as possible to make use of your available tools and rely on them to avoid hallucination or appearing dumb.\n\
            Always be sure of the output of your tools.\n\
            Try to sound friendly and easy to understand.\n\
            You make sure to utilize the policies to answer policy-related queries",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

llm_with_tools = llm.bind_tools(tools)

agent = (
    {
        "input": lambda x: x["input"],
        "chat_history": lambda x: x["chat_history"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)


def agent_invoke(prompt, chat_history=[""]):
    return agent_executor.invoke({"input": prompt, "chat_history": chat_history})[
        "output"
    ]


# print(agent_invoke("What is the status of my order"))
