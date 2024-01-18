# Fallow chatbot
import streamlit as st
from openai import OpenAI
import json
import datetime as dt
import time
import requests

#load info from the info file
with open("info.json") as f:
    info = json.load(f)
    thread = info["thread_id"]
    assistant_ai = info["assistant_id"]

def getAvailableBookings(day, party_size):
    url = "https://api.headswap.com/getAvailableBookings"
    params = {
        "day": day,
        "party_size": party_size
    }

    weekday = dt.datetime.strptime(day, "%Y-%m-%d").strftime("%A")

    response = requests.get(url, params=params).json()
    results = response["results"]

    ai_return = f"Booking for {weekday} {day} \n"
    for i, result in enumerate(results):
        ai_return += f"{i+1}. time: {result['time']}, type: {result['type']}, amount_of_tables_that_fit_{party_size}_guests: {result['quantity']} \n"

    return ai_return

def display_messages():
    thread_messages = client.beta.threads.messages.list(
    thread_id=thread
    ).data
    for thread_message in thread_messages[::-1]:
        role = thread_message.role
        contents = thread_message.content
        for content in contents:
            with st.chat_message(role):
                st.write(content.text.value.split("User: ")[-1])

def create_new_thread():
    # Create a new thread
    thread = client.beta.threads.create()
    info["thread_id"] = thread.id
    with open("info.json", "w") as f:
        json.dump(info, f)
    st.rerun()

with st.sidebar:
    api_key = st.text_input("API key")
    client = OpenAI(api_key=api_key)
    if st.button("Create new thread"):
        create_new_thread()

if not api_key:
    st.warning("Please enter your API key")
    st.stop()

image = st.image("welcome.jpg")

display_messages()

# now to string
now = dt.datetime.now().strftime("%A %Y-%m-%d %H:%M:%S")

prompt = st.chat_input('User')

if prompt:
    prompt = f"{now} User: {prompt}"
    with st.chat_message("user"):
        st.write(prompt.split("User: ")[-1])

    message = client.beta.threads.messages.create(
        thread_id=thread,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=thread,
        assistant_id=assistant_ai,
    )

    # Get the response from the AI
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread,
            run_id=run.id
        )
        time.sleep(1)

        if run.status == "requires_action":
            tools_to_call = run.required_action.submit_tool_outputs.tool_calls
            
            results = []
            for tool in tools_to_call:
                # Get the function to call
                function = tool.function
                arguments = json.loads(function.arguments)
                function_name = function.name

                with st.chat_message("server"):
                    st.write(f"Calling {function_name} with arguments {arguments}")

                if function_name == "getAvailableBookings":
                    result = getAvailableBookings(arguments['day'], arguments['party_size'])

                results.append({"tool_call_id": tool.id, "output": result})
            
            # Submit the result
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread,
                run_id=run.id,
                tool_outputs=results
            )

    
    thread_messages = client.beta.threads.messages.list(
        thread_id=thread
    )

    with st.chat_message("assistant"):
        st.write(thread_messages.data[0].content[0].text.value)