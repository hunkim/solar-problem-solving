# from https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps

import streamlit as st
from langchain_upstage import ChatUpstage as Chat
from langchain_upstage import UpstageGroundednessCheck

from langchain_core.output_parsers import StrOutputParser
from langchain_upstage import UpstageLayoutAnalysisLoader
from langchain_core.prompts import PromptTemplate

import tempfile, os, base64

from agents import default_agents
from code2img import code2img


llm = Chat()
groundedness_check = UpstageGroundednessCheck(use_ocr=True)

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
        }
    )


def get_agent_code(agent, context, analysis_result):
    comon_instruction = """Apply the analysis technique to the context and analysis results and generate python code to generate relevent diagram.
    use matplotlib and generate executable correct code. Please think step by step and write the code.
    All values, variable names, labels and legends should be in English and shorten them for better readability.
    Once again, all values, variable names, labels and legends should be in English.
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

    chain = prompt_template | llm | StrOutputParser()

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

                place_info.info("The response is not good. Let me retry ...")
            else:
                place_info.error("Please double check the response!")

            # store the agent response
            agent_results[agent["name"]] = {"response": response}

        place_diagram_status = st.empty()
        place_diagram = st.empty()

        img = None
        code = None
        with place_diagram_status.status(f"Diagram generation for {agent['name']} ..."):
            for i in range(5):
                try:
                    code = st.write_stream(get_agent_code(agent, context, response))
                    img = code2img(code)
                    if img:
                        st.image(img, caption="Generated Diagram")
                        break
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.warning("Please try again!")

        if img:
            place_diagram.image(img, caption="Generated Diagram")
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

                    st.write("Indexing your document...")
                    layzer = UpstageLayoutAnalysisLoader(file_path, split="page")
                    # For improved memory efficiency, consider using the lazy_load method to load documents page by page.
                    docs = layzer.load()  # or layzer.lazy_load()

                    for doc in docs:
                        context += "\n\n" + str(doc)

        run_follow_up()

        download_context = f"# Solar Problem Solving\n\n## Problem \n{context}\n"
        for agent, result in agent_results.items():
            response = result["response"]
            download_context += f"\n\n## {agent}\n{response}\n\n"
            download_context += "### Generated Diagram\n"
            download_context += f"\n\n{result['code']}\n\n"
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
