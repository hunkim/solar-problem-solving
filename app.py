# from https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit.runtime.scriptrunner import get_script_run_ctx
from langchain_mistralai.chat_models import ChatMistralAI


from langchain_upstage import ChatUpstage as Chat
from langchain_upstage import UpstageGroundednessCheck

from langchain_core.output_parsers import StrOutputParser
from langchain_upstage import UpstageLayoutAnalysisLoader
from langchain_core.prompts import PromptTemplate
from concurrent.futures import ThreadPoolExecutor


import threading


import tempfile, os, base64

from agents import default_agents
from code2img import code2img

model_name = st.secrets.get("SOLAR_MODEL_NAME")
llm = Chat(model=model_name)
groundedness_check = UpstageGroundednessCheck()

agent_results = {}


retries = 3


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
        }
    )


def get_agent_code(agent, context, analysis_result):
    codestral = ChatMistralAI(model="codestral-latest", endpoint="https://codestral.mistral.ai/v1")

    comon_instruction = """Apply the analysis technique to the context and analysis results 
    and generate one complete python code to generate relevent diagram.
    Use matplotlib and generate executable correct and complete code including necessary imports.
    Please think step by step and write the code.
    All values, variable names, labels and legends should be in English and shorten them for better readability.
    Once again, all values, variable names, labels and legends should be in English.
    Please shorten the legend and label names for better readability.
    Only reply with the code.
    """
    prompt_str = (
        agent["instruction"]
        + "\n"
        + comon_instruction
        + "\n\n---\nCONTEXT: {context} \n\n---\nANALYSIS: {analysis_result}"
    )

    for addition_context in agent.get("additional_context", []):
        prompt_str += "\n\n---\n" + addition_context + ": {" + addition_context + "}"

    prompt_template = PromptTemplate.from_template(prompt_str)

    chain = prompt_template | codestral | StrOutputParser()

    return chain.stream(
        {
            "context": context,
            "analysis_result": analysis_result,
        }
    )


def GC_response(agent, context, response):
    instruction = agent["instruction"]
    gc_result = groundedness_check.run(
        {
            "context": f"Context:{context}\n\nInstruction{instruction}",
            "answer": response,
        }
    )

    return gc_result.lower() == "grounded"


def run_problem_solving(agents):
    if st.secrets.get("TEST")=="true":
        agents = agents[:2]

    total_agent_count = len(agents)
    for i, agent in enumerate(agents):
        if i == 0:
            gen_analysis(total_agent_count, i, agent)
        else:
            prev_agent = agents[i - 1]
            prev_response = agent_results[prev_agent["name"]]["response"]

            place_digram_status = st.empty()
            place_digram = st.empty()

            with ThreadPoolExecutor(max_workers=2) as executor:
                ctx = get_script_run_ctx()
                executor.submit(
                    gen_diagram,
                    prev_agent,
                    prev_response,
                    place_digram_status,
                    place_digram,
                    ctx,
                )
                executor.submit(gen_analysis, total_agent_count, i, agent, ctx)

                # for t in executor._threads:
                #    add_script_run_ctx(t)
                # gen_diagram(prev_agent, prev_response, place_digram_status, place_digram)

    # Handle the last diagram
    last_agent = agents[-1]
    last_response = agent_results[last_agent["name"]]["response"]
    place_digram_status = st.empty()
    place_digram = st.empty()
    gen_diagram(last_agent, last_response, place_digram_status, place_digram)

def gen_analysis(total_agent_count, i, agent, ctx=None):
    if ctx:
        add_script_run_ctx(threading.currentThread(), ctx)

    with st.status(
        f"[{(i+1)}/{total_agent_count}] Running {agent['name']} ...",
        expanded=True,
    ):
        place = st.empty()
        place_info = st.empty()
        for i in range(retries):
            response = place.write_stream(get_agent_response(agent, context))
            place_info.info(f"Checking the response. Trial {i+1} ...")
            if GC_response(agent, context, response):
                place_info.success("Agent response is good!")
                break

            place_info.info("The response is not good. Let me retry ...")
        else:
            place_info.error("Please double check the response!")

            # store the agent response
        agent_results[agent["name"]] = {"response": response}
    return response


def gen_diagram(agent, response, place_digram_status, place_digram, ctx=None):
    if ctx:
        add_script_run_ctx(threading.currentThread(), ctx)

    img = None
    code = None
    with place_digram_status.status(f"Diagram generation for {agent['name']} ..."):
        for i in range(retries):
            try:
                code = st.write_stream(get_agent_code(agent, context, response))
                st.info("Generating the diagram ...")
                img = code2img(code)
                if img:
                    st.image(img, caption="Generated Diagram")
                    break
                st.warning("Let me retry ...")
            except Exception as e:
                st.error(f"Error: {e}")
                st.warning("Please try again!")

    if img:
        place_digram.image(img, caption="Generated Diagram")
        agent_results[agent["name"]]["code"] = code
        agent_results[agent["name"]]["img"] = img


if __name__ == "__main__":
    st.title("🌞 Solar Problem Solving")
    st.write(
        """This app is insipred by 
             "Copy and paste these 20 powerful prompts to boost problem-solving" from https://x.com/HeyAbhishekk
"""
    )

    context = st.text_area("Write your context or problems here", height=120)
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

                    layzer = UpstageLayoutAnalysisLoader(
                        file_path, split="page", use_ocr=True
                    )
                    # For improved memory efficiency, consider using the lazy_load method to load documents page by page.
                    docs = layzer.load()  # or layzer.lazy_load()
                    st.write(f"Loaded {len(docs)} pages from {uploaded_file.name}")

                    for doc in docs:
                        context += "\n\n" + str(doc)

        run_problem_solving(default_agents)

        download_context = f"# Solar Problem Solving\n\n## Problem \n{context}\n"
        for agent, result in agent_results.items():
            response = result["response"]
            download_context += f"\n\n## {agent}\n{response}\n\n"

            if "code" in result:
                download_context += "### Generated Diagram\n"
                download_context += f"\n\n{result['code']}\n\n"

            if "img" in result:
                # insert image as base64 first generate base64
                img_base64_txt = base64.b64encode(result["img"]).decode("utf-8")
                download_context += (
                    f"![Generated Diagram](data:image/png;base64,{img_base64_txt})\n\n"
                )

        st.download_button(
            label="Download Results",
            data=download_context,
            file_name="solar_pc.md",
            mime="text/markdown",
        )
