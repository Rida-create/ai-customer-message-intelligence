import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
ANALYZE_ENDPOINT = f"{API_URL}/analyze"

st.set_page_config(
    page_title="Customer Message Intelligence",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 AI Customer Message Intelligence")
st.write(
    "Enter a customer message and the AI system will analyze it."
)

message = st.text_area(
    "Customer Message",
    placeholder="Example: I was charged twice for my subscription and I want a refund.",
    height=180
)

if st.button("🔍 Analyze Message", use_container_width=True):

    if not message.strip():
        st.warning("Please enter a customer message.")
        st.stop()

    with st.spinner("Analyzing customer message..."):
        try:
            response = requests.post(
                ANALYZE_ENDPOINT,
                json={"message": message},
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

        except requests.exceptions.ConnectionError:
            st.error(
                "Could not connect to the FastAPI backend. "
                "Please make sure the backend is running."
            )
            st.stop()

        except requests.exceptions.Timeout:
            st.error("The request timed out. Please try again.")
            st.stop()

        except requests.exceptions.HTTPError as error:
            st.error(f"The backend returned an error: {error}")
            st.stop()

        except requests.exceptions.RequestException as error:
            st.error(f"An API error occurred: {error}")
            st.stop()

        except ValueError:
            st.error("The backend returned an invalid JSON response.")
            st.stop()

    st.success("Message analyzed successfully!")

    st.subheader("📊 Analysis Result")

    st.write("### Category")
    st.info(result.get("category", "Not provided"))

    st.write("### Intent")
    st.info(result.get("intent", "Not provided"))

    st.write("### Priority")
    priority = result.get("priority", "Not provided")

    if str(priority).lower() == "high":
        st.error(priority)
    elif str(priority).lower() == "medium":
        st.warning(priority)
    else:
        st.success(priority)

    st.write("### Sentiment")
    st.info(result.get("sentiment", "Not provided"))

    st.write("### 🔑 Key Information")

    key_information = result.get("key_information", [])

    if isinstance(key_information, list):
        if key_information:
            for item in key_information:
                st.write(f"• {item}")
        else:
            st.write("No key information extracted.")
    else:
        st.write(key_information)

    st.write("### 💬 Suggested Response")

    suggested_response = result.get(
        "suggested_response",
        "No suggested response available."
    )

    st.success(suggested_response)

st.divider()

st.caption(
    "AI Customer Message Intelligence System | Frontend & Testing"
)