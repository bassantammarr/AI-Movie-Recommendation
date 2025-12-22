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
You are an Explainable AI movie recommendation system.

User details:
- Age: {st.session_state.age}
- Mood: {st.session_state.mood}
- Preferred genres: {', '.join(st.session_state.genre) if st.session_state.genre else 'Any'}

Task:
- Recommend 3 to 5 movies.
- For EACH movie, explain WHY it was recommended.
- Explanations must reference:
  - The user's mood
  - Genre preference
  - Emotional tone of the movie
  Format strictly as:

🎬 Movie Title
Genre: ...
Why this movie:
- ...
- ...

Be clear, friendly, and concise.
"""
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}]
    





    with st.chat_message("assistant"):
        response = client.chat.completions.create(

         model="llama-3.1-8b-instant",
         messages=st.session_state.messages,
         )

        assistant_reply = response.choices[0].message.content
        st.markdown(assistant_reply)
        st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

        st.session_state.recommendation_done = True



if st.session_state.recommendation_done:

    if st.button("Explain Recommendations Further 🧠"):
        explanation = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Explainable AI assistant.\n"
                        "Provide deeper reasoning for why these movies suit the user's mood.\n"
                        "Focus on emotional and psychological alignment."
                    )
                },
                {
                    "role": "user",
                    "content": st.session_state.messages[-1]["content"]
                }
            ]
        )

        st.subheader("🧠 Deeper Explanation")
        st.write(explanation.choices[0].message.content)

    if st.button("Start Over 🔄"):
        streamlit_js_eval(js_expressions="parent.window.location.reload()")
