import streamlit as st
import uuid
import asyncio
import httpx

from langchain_core.messages import HumanMessage, AIMessage, messages_from_dict

from sqlite_db import get_distinct_thread_ids, add_thread_to_db, create_thread_db


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
                result = await connect_to_backend(
                    url = "http://127.0.0.1:8000/invoke",
                    json_payload={
                        "thread_id": st.session_state.thread_id,
                        "input": prompt
                    }
                )
                st.session_state.messages.append(AIMessage(content = result["text"]))
                st.write(result["text"])
    
if __name__ == "__main__":
    asyncio.run(main())