import streamlit as st
import anthropic

st.title("Claude API Test")

# Check if API key is set
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.error("❌ No API key found in st.secrets['ANTHROPIC_API_KEY']")
else:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    st.info("Trying a small test request to Claude...")

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say Hello in one sentence."}
            ],
            max_tokens=50
        )
        st.success("✅ Request succeeded!")
        st.markdown("**Claude responded:**")
        st.write(resp.content[0].text.strip())

    except Exception as e:
        st.error(f"❌ Request failed: {e}")
        st.warning("Most likely cause: insufficient API credits or invalid API key.")
