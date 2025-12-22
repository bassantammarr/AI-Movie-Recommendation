import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])


st.set_page_config(page_title="Movie Recommender", page_icon="🎬")
st.title("AI Movie Recommender🎬" )


if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False

if "messages" not in st.session_state:
    st.session_state.messages = []

if "recommendation_done" not in st.session_state:
    st.session_state.recommendation_done = False


def complete_setup():
    st.session_state.setup_complete = True


if not st.session_state.setup_complete:
    
    st.header("Tell me about your mood!" , divider="rainbow")

    if "age" not in st.session_state:
        st.session_state.age = ""
    if "mood" not in st.session_state:
        st.session_state.mood = "happy"
    if "genre" not in st.session_state:
        st.session_state.genre = []
    if "language" not in st.session_state:
        st.session_state.language = "English"

    st.session_state.age = st.text_input("Please enter your age:", value=st.session_state.age)

    st.session_state.mood = st.selectbox(
        "How are you feeling today?",
        ["happy", "sad", "excited", "romantic", "adventurous", "thoughtful"])

    st.session_state.genre = st.multiselect(
        "Preferred genres (select all that apply):",
        ["Action", "Comedy", "Drama", "Horror", "Romance", "Sci-Fi", "Documentary", "Thriller", "Animation"])
    
    
    
    
    if st.button("Recommend Movies" , on_click=complete_setup):
        st.write("Generating recommendations...")


if st.session_state.setup_complete and not st.session_state.feedback_shown and not st.session_state.recommendation_done:
    
    st.info("AI is generating recommendations...", icon="💬")
    system_prompt = f"""
You are an Explainable AI Movie Recommendation System.

User profile:
- Age: {st.session_state.age}
- Mood: {st.session_state.mood}
- Preferred genres: {', '.join(st.session_state.genre) if st.session_state.genre else 'Any'}


Mood interpretation rules:
- happy → light, uplifting, optimistic tone
- sad → comforting, emotional but hopeful
- excited → fast-paced, high energy
- romantic → relationship-driven, emotional
- adventurous → exploration, action, discovery
- thoughtful → deep themes, slow-paced


Recommendation rules:
- Recommend ONLY well-known, real movies
- Avoid obscure or experimental films
- Match BOTH mood and genre
- Age-appropriate content
- Prefer IMDb 7+ style mainstream films

Output exactly 3 movies in this format:

🎬 Title (Year)
Genre: ...
Why it matches:
- Mood alignment
- Genre alignment
"""
    if not st.session_state.messages:
        st.session_state.messages.append({"role": "system", "content": system_prompt})





    with st.chat_message("assistant"):
        response = client.chat.completions.create(

         model="llama-3.1-8b-instant",
         messages=st.session_state.messages,
         )

        assistant_reply = response.choices[0].message.content
        st.markdown(assistant_reply)
        st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

        st.session_state.recommendation_done = True

user_question = st.chat_input("Ask a question about the recommendations 💬")


if user_question and st.session_state.recommendation_done:
    st.session_state.messages.append(
        {"role": "user", "content": user_question}
    )

    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are continuing a conversation about movie recommendations already given. "
                        "Answer ONLY using those movies unless asked otherwise. an search aout the the question and the information he will give you with the previous information given ."
                    )
                }
            ] + st.session_state.messages
        )

        assistant_reply = response.choices[0].message.content
        st.markdown(assistant_reply)

    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_reply}
    )


