"""
COMS — Cloud Orchestrator and Management System
Powered by: Groq (Llama 3.3 70B) + AWS Free Tier + SQLite
"""
import streamlit as st
import time
import json
import csv
import io
from datetime import datetime

# ── PAGE CONFIG (must be first Streamlit call) ───────────────
st.set_page_config(
    page_title="COMS",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── DB INIT ──────────────────────────────────────────────────
from utils.database import init_db
init_db()

# ── AUTH (Streamlit session shim — replaced in Phase 2) ──────
from utils.session import (
    login, set_session, clear_session,
    is_authenticated, current_user, require_role,
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; }
html, body, .stApp { font-family: 'Inter', sans-serif; background: #0a0d14; color: #e6edf3; }

/* ── Login card ─────────────────────────────────────────── */
.login-wrapper {
    display: flex; justify-content: center; align-items: center;
    min-height: 80vh; padding: 40px 16px;
}
.login-card {
    background: #111622; border: 1px solid #21262d; border-radius: 16px;
    padding: 48px 40px; width: 100%; max-width: 420px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}
.login-logo {
    font-size: 2rem; font-weight: 700; color: #00E5A0;
    font-family: 'JetBrains Mono', monospace; letter-spacing: -1px;
    text-align: center; margin-bottom: 4px;
}
.login-sub {
    text-align: center; color: #8b949e; font-size: 0.875rem;
    margin-bottom: 36px;
}

/* ── Sidebar ────────────────────────────────────────────── */
section[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }

.sidebar-logo {
    font-size: 1.3rem; font-weight: 700; color: #00E5A0;
    font-family: 'JetBrains Mono', monospace; margin-bottom: 2px;
}
.sidebar-sub { color: #8b949e; font-size: 0.75rem; margin-bottom: 12px; }

/* ── Badges ─────────────────────────────────────────────── */
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.70rem; font-weight: 600; color: white; letter-spacing: 0.02em;
}
.badge-green  { background: #145a32; color: #00C48C; border: 1px solid #00C48C; }
.badge-blue   { background: #0c2547; color: #4da6ff; border: 1px solid #0070F3; }
.badge-orange { background: #3d2600; color: #F5A623; border: 1px solid #F5A623; }
.badge-red    { background: #3d0c0c; color: #ff6b6b; border: 1px solid #E53E3E; }
.badge-grey   { background: #1c2233; color: #8b949e; border: 1px solid #30363d; }

/* ── Pipeline steps ─────────────────────────────────────── */
.pipeline-step {
    background: #0d1117; border-left: 3px solid #00E5A0;
    padding: 8px 16px; margin: 4px 0; border-radius: 0 8px 8px 0;
    font-family: 'JetBrains Mono', monospace; font-size: 0.80rem; color: #e6edf3;
}
.pipeline-step.error { border-left-color: #E53E3E; }

/* ── Resource / info cards ──────────────────────────────── */
.resource-card {
    background: #0d1117; border: 1px solid #21262d; border-radius: 10px;
    padding: 14px; margin: 6px 0;
}
.security-badge {
    background: #111622; border: 1px solid #21262d; border-radius: 8px;
    padding: 10px 14px; font-size: 0.76rem; color: #8b949e; line-height: 1.5;
}
.warning-box {
    background: #2d2000; border-left: 3px solid #F5A623;
    padding: 8px 14px; border-radius: 0 8px 8px 0;
    font-size: 0.82rem; color: #F5A623; margin: 4px 0;
}
.section-header {
    font-size: 1.4rem; font-weight: 700; color: #e6edf3;
    border-bottom: 1px solid #21262d; padding-bottom: 10px; margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# LOGIN PAGE
# ════════════════════════════════════════════════════════════
def render_login():
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)

    with st.container():
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            st.markdown('<div class="login-logo">COMS</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="login-sub">Cloud Orchestrator and Management System</div>',
                unsafe_allow_html=True,
            )

            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input("Username", placeholder="Enter username")
                password_input = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username_input or not password_input:
                    st.error("Username and password are required.")
                else:
                    user = login(username_input, password_input)
                    if user:
                        set_session(user)
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# GUARD: Show login page if not authenticated
# ════════════════════════════════════════════════════════════
if not is_authenticated():
    render_login()
    st.stop()


# ── Everything below only runs if authenticated ───────────────

from agents.orchestrator import MasterOrchestrator, do_approve, do_reject
from utils.database import get_all_users, create_user
from utils.firestore_db import (
    get_audit_log, get_recent_logs, get_audit_stats,
    get_pending_approvals, get_all_approvals, get_resources,
    get_monthly_spend,
)
from utils.aws_client import AWS_MODE
from utils.rate_limiter import check_rate_limit

_user = current_user()
_uid      = _user["id"]
_username = _user["username"]
_role     = _user["role"]
_is_admin = _role == "admin"
_is_lead  = _role in ("admin", "dev-lead")

# ── Session state init ────────────────────────────────────────
if "orchestrator" not in st.session_state:
    orch = MasterOrchestrator()
    orch.set_user_role(_role)
    orch.set_username(_username)
    orch.set_user_id(_uid)
    st.session_state.orchestrator = orch

if "messages" not in st.session_state:
    st.session_state.messages = []


# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">COMS</div>'
        '<div class="sidebar-sub">Cloud Orchestrator and Management System</div>',
        unsafe_allow_html=True,
    )

    aws_color = "badge-blue" if "Real" in AWS_MODE else "badge-grey"
    role_colors = {"admin": "badge-red", "dev-lead": "badge-orange", "developer": "badge-blue"}
    badge_role = role_colors.get(_role, "badge-grey")

    st.markdown(
        f'<span class="badge badge-green">Online</span> '
        f'<span class="badge {aws_color}">{AWS_MODE}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span style="font-size:0.85rem;color:#e6edf3;">{_username}</span> '
        f'<span class="badge {badge_role}">{_role}</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Build navigation based on role
    nav_options = ["Chat", "My Resources", "Dashboard"]
    if _is_lead:
        nav_options.insert(2, "Approval Queue")
    if _is_admin:
        nav_options += ["All Resources", "User Management", "Audit Log"]

    page = st.radio("Navigation", nav_options, label_visibility="collapsed")

    st.markdown("---")

    # Quick demos
    st.markdown('<span style="font-size:0.8rem;font-weight:600;color:#8b949e;">QUICK DEMOS</span>', unsafe_allow_html=True)
    demos = {
        "List S3 Buckets":         "List all my S3 buckets",
        "Create S3 Bucket":        "Create a private S3 bucket called demo-bucket-coms in ap-south-1",
        "Create Lambda Function":  "Create a Python Lambda function called data-processor",
        "Create SNS Topic":        "Create an SNS topic called order-notifications",
        "Describe EC2 Instances":  "List all EC2 instances",
        "IAM Role (high risk)":    "Create an IAM role for EC2 with full S3 access",
    }
    for label, prompt_text in demos.items():
        if st.button(label, key=f"demo_{label}", use_container_width=True):
            st.session_state.pending_demo = prompt_text

    st.markdown("---")
    if st.button("New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.orchestrator.reset()
        st.rerun()

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        clear_session()
        st.rerun()

    st.markdown(
        '<div class="security-badge">Zero credential exposure — users never see AWS keys. '
        'RBAC enforced per role. All actions audited.</div>',
        unsafe_allow_html=True,
    )


# ── Helper: pipeline renderer ─────────────────────────────────
def _render_pipeline(stages: list):
    if not stages:
        return
    st.markdown("**Pipeline trace:**")
    for stage in stages:
        s = stage.get("status", "")
        ok = s in ("success", "approved")
        icon = "+" if ok else "-" if s == "error" else "~"
        cls = "pipeline-step" if ok else "pipeline-step error"
        st.markdown(
            f'<div class="{cls}">[{icon}] {stage["stage"]} — {stage["time_seconds"]}s</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
# PAGE: CHAT
# ════════════════════════════════════════════════════════════
if page == "Chat":
    st.markdown('<div class="section-header">Chat Interface</div>', unsafe_allow_html=True)
    st.caption(f"Role: **{_role}** · LLM: Llama 3.3 70B (Groq) · AWS: {AWS_MODE}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    prompt = None
    if "pending_demo" in st.session_state:
        prompt = st.session_state.pop("pending_demo")
    else:
        prompt = st.chat_input("Describe your cloud resource request in plain English...")

    if prompt:
        # Rate limiting: 15 NLP requests per minute per user
        allowed, wait = check_rate_limit(_uid, "nlp_request", limit=15, window=60)
        if not allowed:
            st.error(f"Rate limit reached. Please wait {wait} seconds before sending another request.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Processing through pipeline..."):
                result = st.session_state.orchestrator.process_message(prompt)

            response = ""

            if result["status"] == "clarification_needed":
                response = f"**Need more information:**\n\n{result['message']}"
                st.markdown(response)

            elif result["status"] == "denied":
                lines = ["**Request Denied by Policy Engine**\n"]
                for v in result.get("violations", []):
                    lines.append(f"- {v}")
                warnings = result.get("warnings", [])
                if warnings:
                    lines.append("\n**Warnings:**")
                    for w in warnings:
                        lines.append(f"  - {w}")
                response = "\n".join(lines)
                st.markdown(response)

            elif result["status"] == "pending_approval":
                risk = result.get("risk_result", {})
                aid  = result.get("approval_id", "?")
                response = (
                    f"**Awaiting Admin Approval** — Request #{aid}\n\n"
                    f"**Risk Level:** {risk.get('tier', 'High Risk')}\n\n"
                    f"**Reason:** {risk.get('reason', '')}\n\n"
                    "Navigate to **Approval Queue** in the sidebar to track status."
                )
                st.markdown(response)
                _render_pipeline(result.get("pipeline_stages", []))

            elif result["status"] == "executed":
                resource = result.get("resource", {})
                st.markdown(f"**{result['message']}**")
                if resource:
                    st.markdown("**Provisioned Resource:**")
                    num_cols = min(len(resource), 4)
                    if num_cols > 0:
                        cols = st.columns(num_cols)
                        for i, (key, val) in enumerate(resource.items()):
                            with cols[i % num_cols]:
                                st.metric(label=key.replace("_", " ").title(), value=str(val))
                _render_pipeline(result.get("pipeline_stages", []))
                response = f"Done in {result['total_time_seconds']}s"

            elif result["status"] == "error":
                response = f"**Error:** {result.get('message', 'Unknown error')}"
                st.markdown(response)

            st.session_state.messages.append({
                "role": "assistant",
                "content": response or result.get("message", ""),
            })


# ════════════════════════════════════════════════════════════
# PAGE: MY RESOURCES (own user's resources)
# ════════════════════════════════════════════════════════════
elif page == "My Resources":
    st.markdown('<div class="section-header">My Resources</div>', unsafe_allow_html=True)
    st.caption("Resources provisioned by your account through COMS")

    resources = get_resources("active", user_id=_uid)

    if not resources:
        st.info("No active resources yet. Use Chat to provision cloud resources.")
    else:
        service_icons = {
            "S3 Bucket": "S3",
            "EC2 Instance": "EC2",
            "IAM Role": "IAM",
            "Lambda Function": "Lambda",
            "SNS Topic": "SNS",
            "CloudWatch Log Group": "Logs",
        }

        by_type: dict = {}
        for r in resources:
            by_type.setdefault(r["resource_type"], []).append(r)

        for rtype, items in by_type.items():
            label = service_icons.get(rtype, rtype)
            st.markdown(f"**{label} — {rtype}** ({len(items)})")
            for item in items:
                with st.expander(f"{item['resource_name']} — {item['timestamp'][:19]}", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Region", item.get("region") or "global")
                    c2.metric("Status", item["status"])
                    c3.metric("Created", item["timestamp"][:10])
                    if item.get("details"):
                        st.json(item["details"])
            st.markdown("---")

        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=[
            "id", "timestamp", "resource_type", "resource_name", "region", "status"
        ])
        writer.writeheader()
        for r in resources:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "Export (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"coms_my_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
elif page == "Dashboard":
    st.markdown('<div class="section-header">Dashboard</div>', unsafe_allow_html=True)

    stats        = get_audit_stats()
    my_resources = get_resources("active", user_id=_uid)
    pending_count = len(get_pending_approvals())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", stats["total"])
    c2.metric("Successful", stats["success"])
    c3.metric("Errors", stats["errors"])
    c4.metric("My Active Resources", len(my_resources))

    if _is_lead:
        st.metric("Pending Approvals", pending_count, delta=None)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Traditional ITSM vs COMS**")
        st.error("Traditional: Ticket → Approval → Provisioning — 4 to 48 hours")
        st.success("COMS: NLP → Validate → Execute — under 5 seconds")

    with col_right:
        st.markdown("**AWS Free Tier Status**")
        st.info(
            "S3: 5 GB/month · EC2: 750 hrs t2.micro · Lambda: 1M req/month · "
            "SNS: 1M publishes · IAM: Free · CloudWatch: 5 GB ingestion\n\n"
            f"Mode: **{AWS_MODE}**"
        )

    st.markdown("---")
    st.markdown("**Recent Activity**")
    recent = get_recent_logs(10)
    if recent:
        for entry in recent:
            ok = entry["status"] in ("success", "approved")
            cls = "pipeline-step" if ok else "pipeline-step error"
            ts  = entry["timestamp"][:19] if entry.get("timestamp") else "?"
            st.markdown(
                f'<div class="{cls}">[{"+" if ok else "-"}] {entry["action"]} '
                f'| {ts} | {entry["status"].upper()}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No activity recorded yet.")


# ════════════════════════════════════════════════════════════
# PAGE: APPROVAL QUEUE (admin + dev-lead only)
# ════════════════════════════════════════════════════════════
elif page == "Approval Queue":
    require_role("dev-lead")
    st.markdown('<div class="section-header">Approval Queue</div>', unsafe_allow_html=True)

    tab_pending, tab_history = st.tabs(["Pending", "History"])

    with tab_pending:
        pending = get_pending_approvals()
        if not pending:
            st.success("No pending approvals. Queue is clear.")
        else:
            st.info(f"**{len(pending)} request(s) awaiting approval**")
            for entry in pending:
                parsed = entry["parsed_request"]
                risk   = entry["risk_result"]
                with st.expander(
                    f"#{entry['id']} — {parsed.get('intent','?')} | {entry['user_role']} | {entry['timestamp']}",
                    expanded=True,
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Intent:** `{parsed.get('intent')}`")
                        st.markdown(f"**Service:** `{parsed.get('service')}`")
                        st.markdown(f"**Risk Tier:** {risk.get('tier')}")
                        st.markdown(f"**Requested by role:** `{entry['user_role']}`")
                    with c2:
                        st.markdown("**Parameters:**")
                        st.json(parsed.get("parameters", {}))

                    reject_reason = st.text_input(
                        "Rejection reason (optional)", key=f"reason_{entry['id']}"
                    )
                    btn_a, btn_r = st.columns(2)
                    with btn_a:
                        if st.button(f"Approve #{entry['id']}", key=f"approve_{entry['id']}", use_container_width=True):
                            res = do_approve(entry["id"], _username)
                            if res["status"] == "executed":
                                st.success(f"Approved and executed: {res['message']}")
                            else:
                                st.error(f"Execution failed: {res.get('message')}")
                            time.sleep(0.5)
                            st.rerun()
                    with btn_r:
                        if st.button(f"Reject #{entry['id']}", key=f"reject_{entry['id']}", use_container_width=True):
                            do_reject(entry["id"], reject_reason or "Rejected by admin", _username)
                            st.warning("Request rejected.")
                            time.sleep(0.5)
                            st.rerun()

    with tab_history:
        all_approvals = get_all_approvals(50)
        resolved = [a for a in all_approvals if a["status"] != "pending"]
        if not resolved:
            st.info("No resolved approvals yet.")
        else:
            for a in resolved:
                ok  = a["status"] == "approved"
                cls = "pipeline-step" if ok else "pipeline-step error"
                st.markdown(
                    f'<div class="{cls}">[{"+" if ok else "-"}] #{a["id"]} — '
                    f'{a["parsed_request"].get("intent","?")} | '
                    f'{a["status"].upper()} | {(a.get("resolved_at") or "?")[:19]} '
                    f'by {a.get("resolved_by","?")}</div>',
                    unsafe_allow_html=True,
                )


# ════════════════════════════════════════════════════════════
# PAGE: ALL RESOURCES (admin only)
# ════════════════════════════════════════════════════════════
elif page == "All Resources":
    require_role("admin")
    st.markdown('<div class="section-header">All Resources</div>', unsafe_allow_html=True)
    st.caption("All resources provisioned through COMS across all users")

    resources = get_resources("active")

    if not resources:
        st.info("No active resources provisioned yet.")
    else:
        service_icons = {
            "S3 Bucket": "S3", "EC2 Instance": "EC2", "IAM Role": "IAM",
            "Lambda Function": "Lambda", "SNS Topic": "SNS", "CloudWatch Log Group": "Logs",
        }
        by_type: dict = {}
        for r in resources:
            by_type.setdefault(r["resource_type"], []).append(r)

        for rtype, items in by_type.items():
            label = service_icons.get(rtype, rtype)
            st.markdown(f"**{label} — {rtype}** ({len(items)})")
            for item in items:
                with st.expander(f"{item['resource_name']} — {item['timestamp'][:19]}", expanded=False):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Region", item.get("region") or "global")
                    c2.metric("Owner (user_id)", str(item.get("user_id") or "—"))
                    c3.metric("Role", item.get("created_by_role") or "—")
                    c4.metric("Status", item["status"])
                    if item.get("details"):
                        st.json(item["details"])
            st.markdown("---")

        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=[
            "id", "timestamp", "resource_type", "resource_name",
            "region", "status", "user_id", "created_by_role"
        ])
        writer.writeheader()
        for r in resources:
            writer.writerow({k: r.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "Export All Resources (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"coms_all_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════
# PAGE: USER MANAGEMENT (admin only)
# ════════════════════════════════════════════════════════════
elif page == "User Management":
    require_role("admin")
    st.markdown('<div class="section-header">User Management</div>', unsafe_allow_html=True)

    users = get_all_users()
    st.markdown(f"**{len(users)} registered users**")

    role_colors = {"admin": "badge-red", "dev-lead": "badge-orange", "developer": "badge-blue"}

    for u in users:
        badge_cls = role_colors.get(u["role"], "badge-grey")
        active_str = "Active" if u["is_active"] else "Inactive"
        st.markdown(
            f'<div class="resource-card">'
            f'<b>{u["username"]}</b> &nbsp;'
            f'<span class="badge {badge_cls}">{u["role"]}</span> &nbsp;'
            f'<span class="badge badge-grey">{active_str}</span><br>'
            f'<span style="font-size:0.78rem;color:#8b949e;">Created: {u["created_at"][:19]} &nbsp;|&nbsp; ID: {u["id"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("**Create New User**")
    with st.form("create_user_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_username = st.text_input("Username")
        with col2:
            new_password = st.text_input("Password", type="password")
        with col3:
            new_role = st.selectbox("Role", ["developer", "dev-lead", "admin"])
        submitted = st.form_submit_button("Create User", use_container_width=True)

    if submitted:
        if not new_username or not new_password:
            st.error("Username and password are required.")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters.")
        else:
            try:
                result = create_user(new_username.strip(), new_password, new_role)
                st.success(f"User '{result['username']}' created with role '{result['role']}'.")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                if "UNIQUE" in str(e):
                    st.error(f"Username '{new_username}' already exists.")
                else:
                    st.error(f"Failed to create user: {e}")


# ════════════════════════════════════════════════════════════
# PAGE: AUDIT LOG (admin only)
# ════════════════════════════════════════════════════════════
elif page == "Audit Log":
    require_role("admin")
    st.markdown('<div class="section-header">Audit Trail</div>', unsafe_allow_html=True)

    logs = get_audit_log(500)

    if not logs:
        st.info("No actions recorded yet.")
    else:
        fc1, fc2 = st.columns(2)
        with fc1:
            status_filter = st.multiselect(
                "Filter by status",
                ["success", "error", "denied", "pending", "approved", "rejected"],
                default=[],
            )
        with fc2:
            action_filter = st.text_input("Filter by action keyword", "")

        filtered = logs
        if status_filter:
            filtered = [l for l in filtered if l["status"] in status_filter]
        if action_filter:
            filtered = [l for l in filtered if action_filter.lower() in l["action"].lower()]

        st.caption(f"Showing {len(filtered)} of {len(logs)} entries")

        for entry in filtered:
            ok  = entry["status"] in ("success", "approved")
            cls = "pipeline-step" if ok else "pipeline-step error"
            ts   = (entry.get("timestamp") or "?")[:19]
            role = f" | {entry['user_role']}" if entry.get("user_role") else ""
            uid  = f" | uid:{entry['user_id']}" if entry.get("user_id") else ""
            dur  = f" | {entry['duration_s']}s" if entry.get("duration_s") else ""
            st.markdown(
                f'<div class="{cls}">[{"+" if ok else "-"}] <b>{entry["action"]}</b>'
                f' | {ts}{role}{uid}{dur}'
                f' | <b>{entry["status"].upper()}</b></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        csv_buf = io.StringIO()
        writer = csv.DictWriter(csv_buf, fieldnames=[
            "id", "timestamp", "action", "status", "user_id", "user_role", "duration_s", "details"
        ])
        writer.writeheader()
        for l in filtered:
            writer.writerow({k: l.get(k, "") for k in writer.fieldnames})
        st.download_button(
            "Export Audit Log (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"coms_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
