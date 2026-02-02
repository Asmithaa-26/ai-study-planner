import streamlit as st
import sqlite3
from datetime import date

st.set_page_config(page_title="AI Study Planner", layout="wide")

# ---------------- DB ----------------
conn = sqlite3.connect("planner.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS goals(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
goal_type TEXT,
start TEXT,
end TEXT,
hours INTEGER,
days TEXT,
intensity TEXT,
current_day INTEGER DEFAULT 1
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY AUTOINCREMENT,
goal_id INTEGER,
day INTEGER,
task TEXT,
milestone TEXT,
done INTEGER DEFAULT 0
)
""")

conn.commit()

# ---------------- PLAN LOGIC ----------------
def generate_plan(goal, total_days, intensity):

    topics = [
        "Fundamentals",
        "Core Concepts",
        "Practice",
        "Advanced Topics",
        "Projects",
        "Revision"
    ]

    repeat = 2 if intensity=="Light" else 1 if intensity=="Moderate" else 0.7

    plan=[]
    per_topic=max(1,int((total_days/len(topics))*repeat))

    day=1
    for t in topics:
        for _ in range(per_topic):
            plan.append((day,f"{t} of {goal}",t))
            day+=1

    while len(plan)<total_days:
        plan.append((day,f"Practice {goal}","Practice"))
        day+=1

    return plan


def create_goal(data):
    start=date.today()
    total_days=(data["end"]-start).days

    if total_days<=0:
        st.error("End date must be future")
        return

    plan=generate_plan(data["name"],total_days,data["intensity"])

    c.execute("""
    INSERT INTO goals(name,goal_type,start,end,hours,days,intensity,current_day)
    VALUES(?,?,?,?,?,?,?,1)
    """,(
        data["name"],
        data["type"],
        str(start),
        str(data["end"]),
        data["hours"],
        ",".join(data["study_days"]),
        data["intensity"]
    ))

    gid=c.lastrowid

    for d,task,ms in plan:
        c.execute("""
        INSERT INTO tasks(goal_id,day,task,milestone)
        VALUES(?,?,?,?)
        """,(gid,d,f"Day {d}: {task}",ms))

    conn.commit()

# ---------------- UI ----------------
st.title("📘 AI Study Planner")

menu=st.sidebar.radio("Navigation",["Create Goal","Dashboard"])

# ---------------- CREATE ----------------
if menu=="Create Goal":

    st.subheader("🎯 Goal Definition")

    name=st.text_input("Learning Goal")
    goal_type=st.selectbox("Goal Type",["Certification","Exam","Skill Mastery"])
    end=st.date_input("Target Date")

    st.subheader("⏱ Time Availability")

    hours=st.slider("Hours per day",1,8,2)
    study_days=st.multiselect("Preferred Study Days",
                              ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    intensity=st.selectbox("Study Intensity",
                           ["Light","Moderate","Intensive"])

    if st.button("Generate Study Plan"):
        create_goal({
            "name":name,
            "type":goal_type,
            "end":end,
            "hours":hours,
            "study_days":study_days,
            "intensity":intensity
        })
        st.success("Study Plan Created!")
        st.rerun()

# ---------------- DASHBOARD ----------------
if menu=="Dashboard":

    goals=c.execute("SELECT * FROM goals").fetchall()

    if not goals:
        st.info("Create a goal first")
        st.stop()

    gmap={g[1]:g for g in goals}
    chosen=st.selectbox("Select Goal",gmap.keys())

    g=gmap[chosen]
    gid=g[0]

    day_no=g[8]  # manual progression day

    tasks=c.execute(
        "SELECT * FROM tasks WHERE goal_id=?",
        (gid,)
    ).fetchall()

    done=sum(t[5] for t in tasks)
    progress=done/len(tasks) if tasks else 0

    col1,col2,col3=st.columns(3)
    col1.metric("Completion",f"{int(progress*100)}%")
    col2.metric("Tasks Done",done)
    col3.metric("Current Day",day_no)

    st.progress(progress)

    # -------- TODAY TASK --------
    st.subheader("📌 Today's Tasks")

    today_tasks=[t for t in tasks if t[2]==day_no]

    if not today_tasks:
        st.success("All tasks complete 🎉")
    else:
        for t in today_tasks:
            chk=st.checkbox(t[3],value=bool(t[5]))
            c.execute("UPDATE tasks SET done=? WHERE id=?",
                      (1 if chk else 0,t[0]))

    conn.commit()

    # -------- NEXT DAY BUTTON --------
    if st.button("➡️ Move to Next Day"):
        c.execute(
            "UPDATE goals SET current_day=current_day+1 WHERE id=?",
            (gid,)
        )
        conn.commit()
        st.rerun()

    # -------- MILESTONES --------
    st.subheader("🏁 Milestones")

    ms=set(t[4] for t in tasks)
    for m in ms:
        m_tasks=[t for t in tasks if t[4]==m]
        if all(t[5] for t in m_tasks):
            st.success(f"✔ {m}")
        else:
            st.write(f"⏳ {m}")

    # -------- SMART SUGGESTIONS --------
    expected=day_no/len(tasks) if tasks else 0

    st.subheader("🤖 Smart Suggestions")

    if progress<expected:
        st.warning("You're behind. Increase study time.")
    else:
        st.success("You're on track!")

    if progress<0.3:
        st.info("Small steps daily lead to success 💪")
    elif progress<0.7:
        st.info("Consistency is your superpower 🚀")
    else:
        st.success("You're close to mastery 🎯")
