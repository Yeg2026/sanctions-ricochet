# =============================================================================
# app.py  -  "Isolate or reroute?"  Research Ricochet game
# -----------------------------------------------------------------------------
# Visitors:  https://<your-app>.streamlit.app
# Results:   https://<your-app>.streamlit.app/?view=results
# Figures:   Hillingdon, Kizys and Scaramozzino, "Sanctions without Isolation"
#            (BACI bilateral trade data, 2017-2024).
# =============================================================================

import csv
import threading
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# [1] Settings ----------------------------------------------------------------
RESET_PIN = "ricochet"          # change this before the event
DATA_FILE = Path(__file__).parent / "responses.csv"
AUTHORS = "Hillingdon, Kizys and Scaramozzino, Sanctions without Isolation"

st.set_page_config(page_title="Isolate or reroute?", page_icon="🛢️",
                   layout="centered")


# [2] Shared storage (one file, one lock, shared by every visitor) -------------
@st.cache_resource
def get_lock():
    return threading.Lock()


def record(kind, value):
    """Append one event: kind is 'vote' or 'score'."""
    with get_lock():
        new_file = not DATA_FILE.exists()
        with open(DATA_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["time", "kind", "value"])
            writer.writerow([datetime.now().isoformat(timespec="seconds"),
                             kind, value])


def load():
    with get_lock():
        if not DATA_FILE.exists():
            return pd.DataFrame(columns=["time", "kind", "value"])
        return pd.read_csv(DATA_FILE, dtype=str)


def vote_split():
    df = load()
    votes = df[df["kind"] == "vote"]["value"]
    return int((votes == "Isolate").sum()), int((votes == "Reroute").sum())


# [3] Questions ---------------------------------------------------------------
QUESTIONS = [
    {
        "q": "Between 2021 and 2024, how did the volume of crude oil that "
             "Russia exported change?",
        "options": ["Fell by about 60%", "Fell by about 30%",
                    "Fell by about 9%", "Rose by about 10%"],
        "answer": "Fell by about 9%",
        "reveal": "It fell by only 9.2%. EU imports of Russian crude dropped "
                  "from 112.8 to 12.7 million tonnes, yet the total barely "
                  "moved. The oil found other buyers.",
        "chart": "eu",
    },
    {
        "q": "Which country took in most of the Russian crude that Europe "
             "stopped buying?",
        "options": ["China", "India", "Türkiye", "United Arab Emirates"],
        "answer": "India",
        "reveal": "India. Its purchases rose from about 2 to about 73 million "
                  "tonnes a year. China added a further 24 million tonnes. "
                  "Two buyers absorbed almost all of it.",
        "chart": "absorbers",
    },
    {
        "q": "The sanctioning countries had to buy replacement oil elsewhere. "
             "What happened to the price they paid, compared with the world "
             "price?",
        "options": ["They paid less than the world price",
                    "No real change",
                    "They paid a premium of about 6%",
                    "They paid a premium of about 30%"],
        "answer": "They paid a premium of about 6%",
        "reveal": "Before 2022 they paid slightly below the world price. "
                  "Over 2022 to 2024 they paid a premium of 5.8% on average, "
                  "with a peak of 13.8% in 2023.",
        "chart": "premium",
    },
]


# [4] Charts ------------------------------------------------------------------
def chart_eu():
    df = pd.DataFrame({"Year": ["2021", "2024"], "Mt": [112.8, 12.7]})
    base = alt.Chart(df).encode(
        x=alt.X("Year:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Mt:Q", title="EU imports of Russian crude (million tonnes)"))
    return (base.mark_bar(color="#2a6f97", size=60)
            + base.mark_text(dy=-8, fontSize=14).encode(text="Mt:Q")
            ).properties(height=280)


def chart_absorbers():
    df = pd.DataFrame({
        "Country": ["India", "India", "China", "China"],
        "Period": ["2019-21", "2022-24", "2019-21", "2022-24"],
        "Mt": [2.1, 72.6, 74.1, 98.1]})
    base = alt.Chart(df).encode(
        x=alt.X("Period:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Mt:Q", title="Russian crude bought per year (million tonnes)"),
        color=alt.Color("Period:N", legend=None,
                        scale=alt.Scale(range=["#a9bcd0", "#2a6f97"])))
    layer = base.mark_bar(size=40) + base.mark_text(
        dy=-8, fontSize=13, color="#333").encode(text="Mt:Q")
    return layer.properties(height=260, width=140).facet(
        column=alt.Column("Country:N", title=None,
                          header=alt.Header(labelFontSize=15)))


def chart_premium():
    df = pd.DataFrame({
        "Year": ["2019", "2020", "2021", "2022", "2023", "2024"],
        "Premium": [0.93, -2.87, -0.64, -2.47, 13.83, 5.99]})
    df["Sanctions"] = df["Year"].astype(int) >= 2022
    return alt.Chart(df).mark_bar(size=34).encode(
        x=alt.X("Year:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Premium:Q",
                title="Coalition price above world price (%)"),
        color=alt.Color("Sanctions:N", legend=None,
                        scale=alt.Scale(domain=[False, True],
                                        range=["#a9bcd0", "#2a6f97"])),
    ).properties(height=280)


CHARTS = {"eu": chart_eu, "absorbers": chart_absorbers,
          "premium": chart_premium}


# [5] Results page (for the presenter) ----------------------------------------
def results_page():
    st.title("Live results")
    st.caption("Do sanctions isolate an economy, or just reroute its trade?")

    @st.fragment(run_every=5)
    def live():
        df = load()
        iso, rer = vote_split()
        total = iso + rer
        scores = pd.to_numeric(df[df["kind"] == "score"]["value"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Votes", total)
        c2.metric("Finished the game", len(scores))
        c3.metric("Average score",
                  f"{scores.mean():.1f} / 3" if len(scores) else "n/a")
        if total:
            tally = pd.DataFrame({
                "Answer": ["Isolate", "Reroute"], "Votes": [iso, rer],
                "Label": [f"{iso} ({iso / total:.0%})",
                          f"{rer} ({rer / total:.0%})"]})
            base = alt.Chart(tally).encode(
                y=alt.Y("Answer:N", title=None,
                        axis=alt.Axis(labelFontSize=18)),
                x=alt.X("Votes:Q", title=None,
                        axis=alt.Axis(tickMinStep=1)))
            st.altair_chart(
                (base.mark_bar(color="#2a6f97", size=50)
                 + base.mark_text(align="left", dx=6, fontSize=18)
                 .encode(text="Label:N")).properties(height=200),
                width="stretch")
        else:
            st.info("No votes yet.")

    live()

    st.divider()
    st.download_button("Download all responses (CSV)",
                       load().to_csv(index=False),
                       file_name="ricochet_responses.csv")
    with st.expander("Reset the count (after testing)"):
        pin = st.text_input("PIN", type="password")
        if st.button("Delete all responses"):
            if pin == RESET_PIN:
                with get_lock():
                    DATA_FILE.unlink(missing_ok=True)
                st.success("Count reset.")
            else:
                st.error("Wrong PIN.")


# [6] Game (for visitors) -----------------------------------------------------
def game_page():
    ss = st.session_state
    ss.setdefault("step", 0)       # 0 = vote, 1..3 = questions, 4 = end
    ss.setdefault("score", 0)
    ss.setdefault("answered", False)

    # --- Opening vote ---
    if ss.step == 0:
        st.title("Isolate or reroute?")
        st.write("In 2022 the EU, the G7 and their allies stopped buying "
                 "Russian oil.")
        st.subheader("What do you think happened?")
        c1, c2 = st.columns(2)
        if c1.button("🚫  Sanctions isolated Russia's oil trade",
                     width="stretch"):
            ss.vote = "Isolate"
        if c2.button("🔀  The trade simply went elsewhere",
                     width="stretch"):
            ss.vote = "Reroute"
        if "vote" in ss:
            record("vote", ss.vote)
            ss.step = 1
            st.rerun()
        st.caption("One vote, three quick questions, about a minute.")
        return

    # --- Questions ---
    if 1 <= ss.step <= len(QUESTIONS):
        if ss.step == 1 and not ss.answered:
            iso, rer = vote_split()
            total = max(iso + rer, 1)
            st.info(f"So far {iso / total:.0%} of visitors say isolate and "
                    f"{rer / total:.0%} say reroute. Now test your instinct.")

        item = QUESTIONS[ss.step - 1]
        st.progress(ss.step / len(QUESTIONS),
                    text=f"Question {ss.step} of {len(QUESTIONS)}")
        st.subheader(item["q"])

        if not ss.answered:
            choice = st.radio("Your guess", item["options"], index=None,
                              label_visibility="collapsed")
            if st.button("Lock in my guess", type="primary",
                         disabled=choice is None):
                ss.choice = choice
                ss.answered = True
                if choice == item["answer"]:
                    ss.score += 1
                st.rerun()
        else:
            if ss.choice == item["answer"]:
                st.success(f"Correct: {item['answer']}")
            else:
                st.error(f"You said: {ss.choice}")
            st.write(item["reveal"])
            st.altair_chart(CHARTS[item["chart"]](),
                            width="stretch" if item["chart"] != "absorbers" else "content")
            last = ss.step == len(QUESTIONS)
            if st.button("See my result" if last else "Next question",
                         type="primary"):
                ss.step += 1
                ss.answered = False
                if last:
                    record("score", ss.score)
                st.rerun()
        return

    # --- Final screen ---
    st.title(f"You scored {ss.score} out of {len(QUESTIONS)}")
    if ss.score == len(QUESTIONS):
        st.balloons()
    if ss.vote == "Reroute":
        st.success("You voted reroute, and the data agree with you.")
    else:
        st.warning("You voted isolate. The data tell a different story.")
    st.subheader("The short answer")
    st.write(
        "Sanctions rerouted Russian crude. They did not isolate it. India "
        "and China absorbed the oil, and the sanctioning countries paid a "
        "premium for their replacement supply. One member of the coalition "
        "gained: United States crude exports to the EU roughly doubled, "
        "from 37 to 79 million tonnes.")
    iso, rer = vote_split()
    total = max(iso + rer, 1)
    st.write(f"All visitors so far: {iso / total:.0%} isolate, "
             f"{rer / total:.0%} reroute.")
    st.info("Now ask Dr Anna Hillingdon why the senders end up paying.")
    st.caption(f"Source: {AUTHORS}. BACI trade data, 2017 to 2024.")


# [7] Router ------------------------------------------------------------------
if st.query_params.get("view") == "results":
    results_page()
else:
    game_page()
