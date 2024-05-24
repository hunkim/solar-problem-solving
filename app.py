# from https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps

import streamlit as st
from langchain_upstage import ChatUpstage as Chat
from langchain_upstage import UpstageGroundednessCheck

from langchain_core.output_parsers import StrOutputParser
from langchain_upstage import UpstageLayoutAnalysisLoader
from langchain_core.prompts import PromptTemplate

import tempfile, os, json

from agents import default_agents


llm = Chat()
groundedness_check = UpstageGroundednessCheck()

agent_results = {}


def get_agent_response(agent, context):
    comon_instruction = """Apply the analysis technique to the context. 
    Please reply in the language of the context.
    if the context is in English, reply in English.
    if the context is in Korean, reply in Korean.
    """
    prompt_str = (
        agent["instruction"] + "\n" + comon_instruction + "\n\n---\nCONTEXT: {context}"
    )

    for addition_context in agent.get("additional_context", []):
        prompt_str += "\n\n---\n" + addition_context + ": {" + addition_context + "}"

    prompt_template = PromptTemplate.from_template(prompt_str)

    chain = prompt_template | llm | StrOutputParser()

    return chain.stream(
        {
            "context": context,
            **agent_results,
        }
    )


def GC_response(agent, context, response):
    instruction = agent["instruction"]
    additional_context = agent.get("additional_context", [])
    for addition_context in additional_context:
        if addition_context in agent_results:
            context += "\n\n" + agent_results[addition_context]

    gc_result = groundedness_check.run(
        {
            "context": f"Context:{context}\n\nInstruction{instruction}",
            "answer": response,
        }
    )

    return gc_result.lower() == "grounded"


def run_follow_up():
    total_agent_count = len(default_agents)
    for i, agent in enumerate(default_agents):
        with st.status(
            f"[{(i+1)}/{total_agent_count}] Running {agent['name']} ...",
            expanded=True,
        ):
            place = st.empty()
            place_info = st.empty()
            for i in range(3):
                response = place.write_stream(get_agent_response(agent, context))
                place_info.info(f"Checking the response. Trial {i+1} ...")
                if GC_response(agent, context, response):
                    place_info.success("Agent response is good!")
                    break

                place_info.info("The response is no good. Writing a new response ...")
            else:
                place_info.error("Please double check the response!")

            # store the agent response
            agent_results[agent["name"]] = response


if __name__ == "__main__":
    st.title("🌞 Solar Problem Solving")
    st.write("""This app is insipred by 
             "Copy and paste these 20 powerful prompts to boost problem-solving" from https://x.com/HeyAbhishekk
""")

    with st.sidebar:
        st.header(f"Add your conext such as text email or screenshots!")

        context = st.text_area("Paste your context here", height=120)
        uploaded_file = st.file_uploader(
            "Otional: Choose your pdf or image file", type=["png", "jpeg", "jpg", "pdf"]
        )
        button = st.button("Let's Solve!")

    if button and (uploaded_file or context):
        if uploaded_file and uploaded_file.name:
            with st.status("Processing the data ..."):
                with tempfile.TemporaryDirectory() as temp_dir:
                    file_path = os.path.join(temp_dir, uploaded_file.name)

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getvalue())

                    st.write("Indexing your document...")
                    layzer = UpstageLayoutAnalysisLoader(file_path, split="page")
                    # For improved memory efficiency, consider using the lazy_load method to load documents page by page.
                    docs = layzer.load()  # or layzer.lazy_load()

                    for doc in docs:
                        context += "\n\n" + str(doc)

        run_follow_up()
