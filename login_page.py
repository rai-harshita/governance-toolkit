import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Karla:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html,body,.stApp{background:#F4EFE2 !important;}
[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"]{display:none !important;}
.block-container,[data-testid="stMain"] .block-container{max-width:100% !important; padding:0 !important;
  margin:0 !important; background:transparent !important; border:none !important; border-radius:0 !important;}
[data-testid="stHorizontalBlock"]{gap:0 !important; align-items:stretch;}

/* left brand panel */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child{
  background:#4D5B3A; min-height:100vh; padding:3.2rem 3.6rem; position:relative; overflow:hidden;}
/* right sign-in panel */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child,
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child{
  background:#F4EFE2; padding:4rem 4.5rem 2rem; min-height:100vh;}

.lp-shield{position:absolute; right:-70px; bottom:-40px; width:430px; opacity:.09; pointer-events:none;}
.lp-brandrow{display:flex; align-items:center; gap:18px;}
.lp-word{font-family:'Cormorant Garamond',Georgia,serif; font-size:3.6rem; font-weight:500; color:#F3EEDD; line-height:1;}
.lp-tag{font-family:'IBM Plex Mono',monospace; font-size:.68rem; letter-spacing:.34em; text-transform:uppercase;
  color:#C9CFB4; margin-top:10px;}
.lp-sub{font-family:'Karla',sans-serif; color:#E4E1CC; font-size:1.08rem; line-height:1.7; max-width:640px; margin:2.2rem 0 1.6rem;}
.lp-stats{display:flex; flex-wrap:wrap; gap:10px; max-width:640px;}
.lp-stats span{font-family:'IBM Plex Mono',monospace; font-size:.74rem; color:#E4E1CC; padding:7px 13px;
  background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.2); border-radius:2px;}
.lp-rule{border:none; border-top:1px solid rgba(255,255,255,.2); margin:2.6rem 0 2rem; max-width:860px;}
.lp-feats{display:grid; grid-template-columns:repeat(3,1fr); gap:2.2rem; max-width:860px;}
.lp-feats h4{font-family:'Cormorant Garamond',Georgia,serif; font-size:1.7rem; font-weight:500; color:#F3EEDD; margin:.6rem 0 .5rem;}
.lp-feats p{font-family:'Karla',sans-serif; font-size:.88rem; line-height:1.6; color:#C9CFB4; margin:0;}

/* right side brand */
.lp-rbrand{display:flex; align-items:center; justify-content:center; gap:12px; margin-bottom:1.6rem;}
.lp-rword{font-family:'Cormorant Garamond',Georgia,serif; font-size:2.1rem; font-weight:500; color:#3C3226; line-height:1;}
.lp-rtag{font-family:'IBM Plex Mono',monospace; font-size:.6rem; letter-spacing:.3em; text-transform:uppercase; color:#6B6250; margin-top:6px;}
.lp-note{font-family:'Karla',sans-serif; font-size:.78rem; color:#6B6250; text-align:center; max-width:520px; margin:1.4rem auto 0;}

/* sign-in card */
.stTabs{max-width:520px; margin:0 auto; background:#FCF8EE; border:1px solid #DDD6C2; border-radius:6px;
  box-shadow:0 14px 36px rgba(60,50,30,.09);}
[data-baseweb="tab-list"]{gap:0 !important; border-bottom:1px solid #E6DFCB;}
button[data-baseweb="tab"]{flex:1; justify-content:center; height:54px; background:transparent;}
button[data-baseweb="tab"] p{font-family:'Karla',sans-serif; font-weight:500; font-size:.95rem; color:#6B6250;}
button[data-baseweb="tab"][aria-selected="true"] p{color:#2E2A20; font-weight:700;}
[data-baseweb="tab-highlight"]{background:#6F4A2B !important; height:2px !important;}
[data-baseweb="tab-border"]{background:transparent !important;}
[data-testid="stTabPanel"]{padding:1.6rem 2rem 2rem !important;}
[data-testid="stForm"]{border:none !important; padding:0 !important; background:transparent !important; box-shadow:none !important;}
[data-testid="stWidgetLabel"] p{font-family:'Karla',sans-serif; font-weight:700; font-size:.9rem; color:#2E2A20;}
[data-baseweb="input"],[data-baseweb="base-input"]{background:#DDDCC3 !important; border:none !important; border-radius:3px !important;}
[data-baseweb="input"] input{color:#2E2A20 !important; font-family:'Karla',sans-serif; height:46px;}
[data-baseweb="input"] input::placeholder{color:#8C8A74 !important; opacity:1;}
[data-baseweb="input"]:focus-within{box-shadow:0 0 0 2px #B9A98A !important;}
[data-testid="stFormSubmitButton"]>button{width:100%; height:3.1rem; background:#6F4A2B !important; color:#F8F3E6 !important;
  border:none !important; border-radius:3px !important; font-family:'Karla',sans-serif; font-weight:700; letter-spacing:.03em;}
[data-testid="stFormSubmitButton"]>button:hover{background:#5E3E24 !important;}

@media (max-width:900px){
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child{padding:2rem 1.4rem; min-height:auto;}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child,
  [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child{padding:2rem 1rem; min-height:auto;}
  .lp-word{font-size:2.6rem;} .lp-feats{grid-template-columns:1fr;}
}
</style>
"""


def _shield(size, stroke, accent, width=2.5, cls=""):
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">'
            f'<path d="M32 4 L56 14 V32 C56 46 46 56 32 60 C18 56 8 46 8 32 V14 Z" stroke="{stroke}" stroke-width="{width}"/>'
            f'<line x1="32" y1="16" x2="32" y2="46" stroke="{stroke}" stroke-width="{width}"/>'
            f'<line x1="17" y1="24" x2="47" y2="24" stroke="{stroke}" stroke-width="{width}"/>'
            f'<path d="M11 36 Q17 44 23 36 Z M41 36 Q47 44 53 36 Z" stroke="{accent}" stroke-width="{width}"/>'
            f'<circle cx="32" cy="16" r="2.6" fill="{stroke}" stroke="none"/></svg>')


def _icon(kind, color):
    paths = {
        "test": '<path d="M4 19V9M10 19V5M16 19v-8M22 19H2"/>',
        "decide": '<path d="M12 3v6M12 9l-7 6M12 9l7 6"/><circle cx="5" cy="17" r="2"/><circle cx="19" cy="17" r="2"/>',
        "review": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5L16 9.5"/>',
    }
    return (f'<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</svg>')


def render(authenticate, create_user):
    st.markdown(CSS, unsafe_allow_html=True)
    left, right = st.columns([1.35, 1])

    with left:
        st.markdown(
            f'{_shield(430, "#FFFFFF", "#FFFFFF", 2, "lp-shield")}'
            f'<div class="lp-brandrow">{_shield(64, "#F3EEDD", "#D9A27A", 2.2)}'
            '<div><div class="lp-word">AequiGate</div>'
            '<div class="lp-tag">Evidence before deployment</div></div></div>'
            '<p class="lp-sub">A release gate for AI systems. Test fairness, explanations and generative-AI '
            'safety, turn the evidence into a decision, and require a named human to sign off.</p>'
            '<div class="lp-stats"><span>4 release decisions</span><span>9 policy checks</span>'
            '<span>95% confidence intervals</span><span>SHA-256 audit chain</span></div>'
            '<hr class="lp-rule"/>'
            '<div class="lp-feats">'
            f'<div>{_icon("test", "#C9CFB4")}<h4>Test</h4>'
            '<p>Fairness, explainability and prompt-attack checks with uncertainty shown.</p></div>'
            f'<div>{_icon("decide", "#D9A27A")}<h4>Decide</h4>'
            '<p>Every result maps to Pass, Conditional, Block or Human Review.</p></div>'
            f'<div>{_icon("review", "#C9CFB4")}<h4>Review</h4>'
            '<p>A named reviewer approves release. Every action is hash-chained.</p></div>'
            '</div>', unsafe_allow_html=True)

    with right:
        st.markdown(
            f'<div class="lp-rbrand">{_shield(40, "#4D3B26", "#B8795D", 2.4)}'
            '<div><div class="lp-rword">AequiGate</div>'
            '<div class="lp-rtag">Evidence before deployment</div></div></div>', unsafe_allow_html=True)

        tab_in, tab_up = st.tabs(["Sign in", "Create account"])
        with tab_in:
            with st.form("login"):
                u = st.text_input("Username", placeholder="e.g. j.rivera")
                p = st.text_input("Password", type="password", placeholder="At least 8 characters")
                if st.form_submit_button("Sign in", use_container_width=True):
                    user = authenticate(u, p)
                    if user:
                        st.session_state.user = user
                        st.session_state.page = "Audit a System" if user["role"] == "submitter" else "Overview"
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
        with tab_up:
            with st.form("signup"):
                n = st.text_input("Full name or team name", placeholder="e.g. Jordan Rivera")
                u2 = st.text_input("Choose a username", placeholder="e.g. j.rivera")
                p2 = st.text_input("Choose a password", type="password", placeholder="At least 8 characters")
                if st.form_submit_button("Create account", use_container_width=True):
                    try:
                        create_user(u2, p2, "submitter", n or u2)
                        st.success("Account created. Switch to the Sign in tab.")
                    except ValueError as e:
                        st.error(str(e))
        st.markdown('<p class="lp-note">Demonstration-grade login. Reviewer and admin accounts are '
                    'issued by the administrator.</p>', unsafe_allow_html=True)