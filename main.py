import streamlit as st
import uuid
import asyncio
import httpx
from langchain.load import loads
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, messages_from_dict

from sqlite_db import get_distinct_thread_ids, add_thread_to_db, create_thread_db
import config as cfg
import json
from streamlit_oauth import OAuth2Component
load_dotenv()
import os
import nest_asyncio

nest_asyncio.apply()

async def connect_to_backend(
    url, 
    json_payload,
    header = {
        "accept": "application/json",
        "Content-Type": "application/json"          
    },  
    timeout=httpx.Timeout(50.0)
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url = url,
            headers= header,
            json= json_payload,
            timeout=timeout
        )
        result = response.json()
    return result

async def main():

    st.title("PERSONAL ASSISTENT")
    st.set_page_config(
        page_title="PA-AGENT"
    )
    await create_thread_db()
    with st.sidebar:

        if st.button(
            "New-chat",
            use_container_width=True
        ):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = [
                AIMessage(content="Hello, How Can I help You Today!!")
            ]
            st.session_state.new_chat = True
        st.title("Uploader:")
        with st.expander("Upload a PDF", expanded=True):
            upload_file = st.file_uploader("Upload a pdf", type="pdf")
            description = st.text_input("Description")
            if st.button("Upload"):
                if not upload_file:
                    st.sidebar.error("Please upload a PDF file.")
                elif not description:
                    st.sidebar.error("Description is required.")
                else:
                    with st.spinner("⏳ Uploading file..."):
                        try:
                            # Prepare files and data
                            files = {"file": (upload_file.name, upload_file, "application/pdf")}
                            data = {"description": description}

                            # Send POST request
                            with httpx.Client(timeout=httpx.Timeout(200)) as client:
                                response = client.post("http://localhost:8000/upload", files=files, data=data)

                            # Show response
                            if response.status_code == 200:
                                st.sidebar.success("✅ File uploaded successfully!")
                            else:
                                st.sidebar.error(f"❌ Upload failed: {response.status_code}")

                        except Exception as e:
                            st.sidebar.error(f"⚠️ Error: {e}")
        st.title("Permission:")
        with st.expander("Google OAuth", expanded=True):
            oauth2 = OAuth2Component(
                    client_id=os.getenv("CLIENT_ID"),
                    client_secret=os.getenv("CLIENT_SECRET"),
                    authorize_endpoint=cfg.GOOGLE_AUTHORIZE_URL,
                    token_endpoint=cfg.GOOGLE_TOKEN_URL,
                    refresh_token_endpoint=cfg.GOOGLE_REFRESH_TOKEN_URL
                )
            if "gmail_token" not in st.session_state:
                try:
                    with httpx.Client(timeout=httpx.Timeout(50)) as client:
                        response = client.get(
                            url = "http://localhost:8000/get-token"
                        )
                        if response.status_code == 200:
                            token = response.json()
                            if token:
                                st.session_state.gmail_token = oauth2.refresh_token( 
                                    token=token,
                                    force=False
                                )
                                st.success("✅ Gmail authorization successful!")
                                st.rerun()
                            else:
                                raise Exception("no token available")
                except Exception as e: 
                    st.warning("⚠️ Please authorize Gmail access")
                    # Show authorize button
                    result = oauth2.authorize_button(
                        name="🔐 Authorize Gmail",
                        redirect_uri=cfg.REDIRECT_URI,
                        scope=cfg.SCOPES,
                        key="gmail_auth",
                        use_container_width=True,
                        extras_params={"prompt": "consent", "access_type": "offline"}
                    )
                    
                    if result and 'token' in result:
                        await connect_to_backend( 
                            url = "http://localhost:8000/store-json",
                            json_payload= result["token"]
                        )
                        st.session_state.gmail_token = result['token']
                        st.rerun()
            else:
                st.success("✅ Gmail authorization successful!")

        with st.container():         
            st.title("Chats")
        
            threads = await get_distinct_thread_ids()

            for thread_id in threads:
                display_msg = f"chat_{thread_id}"
                with st.container():
                    if st.sidebar.button(display_msg, key=thread_id, use_container_width=True):
                        st.session_state.thread_id = thread_id
                        st.session_state.messages = []
                        st.session_state.new_chat = False
                        st.rerun()

    
    if "new_chat" not in st.session_state:
        st.session_state.new_chat = True

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state or not st.session_state.messages:
        if st.session_state.new_chat:
            st.session_state.messages = [
                AIMessage("How Can I help You Today ?")
            ]
        else:
            result = await connect_to_backend(
                        url = "http://127.0.0.1:8000/history",
                        json_payload={
                            "thread_id": st.session_state.thread_id
                        }
                    )
            if result["messages"]:
                st.session_state.messages = messages_from_dict(result["messages"])
            else:
                st.session_state.messages = [
                    AIMessage("How Can I help You Today ?")
                ]

    for msg in st.session_state.messages:
        if isinstance(msg, AIMessage):
            if msg.content:
                st.chat_message('assistant').write(msg.content)
        if isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)

    if prompt := st.chat_input():
        if st.session_state.new_chat:
            st.session_state.new_chat = False
            await add_thread_to_db(
                thread_id=st.session_state.thread_id,
                title= prompt[:25] + "..." if len(prompt) > 25 else prompt
            )
            
        st.session_state.messages.append(HumanMessage(content=prompt))
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
                container = st.container()  # This container will hold the dynamic Streamlit UI components
                thoughts_placeholder = container.container()
                to_do_placeholder = thoughts_placeholder.empty()  # Container for displaying status messages
                token_placeholder = container.empty()  # Placeholder for displaying progressive token updates
                final_text = ""  # Will store the accumulated text from the model's response
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("POST", 
                        "http://localhost:8000/stream", 
                        json={
                         "thread_id": st.session_state.thread_id,
                            "input": prompt
                        }
                    ) as response:
                        async for event in response.aiter_lines():
                            if not event :
                               continue
                            try: 
                                event = loads(event)
                                kind = event["event"]  # Determine the type of event received
                                if kind == "on_chat_model_stream":
                                    # The event corresponding to a stream of new content (tokens or chunks of text)
                                    addition = event["data"]["chunk"].content  # Extract the new content chunk
                                    final_text += addition  # Append the new content to the accumulated text
                                    if addition:
                                        token_placeholder.write(final_text)  # Update the st placeholder with the progressive response

                                elif kind == "on_tool_start":
                                    # The event signals that a tool is about to be called
                                    with thoughts_placeholder:
                                        print(f"*****{event['name']}*****")
                                        status_placeholder = st.empty()  # Placeholder to show the tool's status
                                        with status_placeholder.status("Calling Tool...", expanded=True) as s:
                                            st.write("Called ", event['name'])  # Show which tool is being called
                                            st.write("Tool input: ")
                                            st.code(event['data'].get('input'))  # Display the input data sent to the tool
                                            st.write("Tool output: ")
                                            output_placeholder = st.empty()  # Placeholder for tool output that will be updated later below
                                            s.update(label="Completed Calling Tool!", expanded=False)  # Update the status once done

                                elif kind == "on_tool_end":
                                    # The event signals the completion of a tool's execution
                                    print(f"*****{event['name']}*****")
                                    with thoughts_placeholder:
                                        # We assume that `on_tool_end` comes after `on_tool_start`, meaning output_placeholder exists
                                        if 'output_placeholder' in locals():
                                            output_placeholder.code(event['data'].get('output').content)  # Display the tool's output
                                elif kind == "on_custom_event":
                                    if event["name"] == "on_todo_update":
                                        with to_do_placeholder.status('TO-DO', expanded=True):
                                            todos = event['data']['todo']
                                            for task in todos:
                                                if task["status"] == "pending":
                                                    st.markdown(f"- [ ] {task['content']}")
                                                elif task["status"] == "in_progress":
                                                    st.markdown(f"🔄 **{task['content']}**")
                                                elif task["status"] == "completed":
                                                    st.markdown(f"- [x] ~~{task['content']}~~")
                            except Exception as e:
                                print(e)
                st.session_state.messages.append(AIMessage(content=final_text))           
    
if __name__ == "__main__":
    asyncio.run(main())