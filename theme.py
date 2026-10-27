import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

CLAY, SAGE, SAGE_D = "#B8795D", "#74866A", "#4E6046"
INK, MUTED, LINE, SURFACE = "#262923", "#6B6F63", "#DEDCD2", "#FFFFFF"
SANS = "'Inter', 'Segoe UI', system-ui, sans-serif"
MONO = "'IBM Plex Mono', Consolas, monospace"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');
:root{--bg:#F6F4EE;--ink:#262923;--sage:#74866A;--sage-d:#5C6F52;--pale:#E3E9DE;--clay:#B8795D;
--line:#DEDCD2;--panel:#FBFAF5;--muted:#6B6F63;
--serif:'DM Serif Display',Georgia,serif;--sans:'Inter','Segoe UI',system-ui,sans-serif;
--mono:'IBM Plex Mono',Consolas,monospace;}
html,body,.stApp{background:#8E9F8C; color:var(--ink); font-family:var(--sans);}
[data-testid="stMain"] .block-container{background:var(--bg); border:1px solid var(--line); border-radius:10px;
  margin:1.1rem auto; padding:2rem 2.4rem 2.4rem; max-width:1180px;}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden; height:0;}
:focus-visible{outline:2px solid var(--sage-d) !important; outline-offset:2px;}
hr{border-color:var(--line);}
h1{font-family:var(--serif) !important; font-weight:400 !important; color:var(--ink) !important;
  font-size:2.3rem !important; padding-bottom:.45rem; border-bottom:1px solid var(--line);
  margin-bottom:.6rem; position:relative;}
h1::after{content:""; position:absolute; left:0; bottom:-1px; width:56px; height:2px; background:var(--clay);}
h2,h3,h4{font-family:var(--sans) !important; font-weight:600 !important; color:var(--ink) !important;}
h2{font-size:1.15rem !important;}
[data-testid="stCaptionContainer"],.stCaption{color:var(--muted);}
[data-testid="stMetric"]{background:var(--panel); border:1px solid var(--line); border-top:2px solid var(--sage);
  border-radius:6px; padding:12px 14px; box-shadow:none;}
[data-testid="stMetricLabel"]{color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em;}
[data-testid="stMetricValue"]{font-family:var(--mono) !important; font-weight:500; font-size:1.65rem; color:var(--ink);}
[data-testid="stMetricDelta"]{font-family:var(--mono); font-size:.74rem;}
.card{background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:14px 18px; margin-bottom:10px;}
.card h3{margin:0 !important; font-size:1.05rem !important;}
.kpi{background:var(--panel); border:1px solid var(--line); border-top:2px solid var(--sage);
  border-radius:6px; padding:14px 16px; min-height:104px;}
.kpi p{margin:0; color:var(--muted); font-size:.7rem; text-transform:uppercase; letter-spacing:.1em;}
.kpi h2{margin:8px 0 0; font-family:var(--mono) !important; font-weight:500 !important; font-size:1.9rem !important;}
[data-testid="stExpander"],[data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--panel); border:1px solid var(--line) !important; border-radius:6px !important; box-shadow:none;}
[data-testid="stExpander"] summary{font-weight:600;}
[data-testid="stDataFrame"]{border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#fff;}
[data-testid="stAlert"]{border-radius:6px;}
.pill{display:inline-block; padding:2px 11px; border-radius:999px; color:#fff; font-family:var(--mono);
  font-weight:500; font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; vertical-align:middle;}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{
  border-radius:5px; border:1px solid var(--line); background:#fff; color:var(--ink); font-weight:500;
  transition:background .15s,border-color .15s;}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--sage); background:var(--pale); color:var(--ink);}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primary"],
button[data-testid="stBaseButton-primary"]{background:var(--sage-d); border:1px solid var(--sage-d); color:#fff;}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  background:#fff !important; border:1px solid var(--line) !important; border-radius:5px !important;}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within{
  border-color:var(--sage-d) !important; box-shadow:0 0 0 2px var(--pale);}
[data-baseweb="tab-highlight"]{background:var(--sage-d) !important;}
[data-testid="stFileUploaderDropzone"]{background:#fff; border:1px dashed var(--sage); border-radius:6px;}

[data-testid="stSidebar"]{background:#52674A; border-right:none;}
[data-testid="stSidebar"]>div:first-child{padding-top:1.2rem;}
.brandrow{display:flex; align-items:center; gap:10px; margin-bottom:6px;}
[data-testid="stSidebar"] .brand{font-family:var(--serif) !important; font-size:1.35rem !important; font-weight:400;
  margin:0; line-height:1.15; color:#F6F4EE !important;}
[data-testid="stSidebar"] .brand-sub,[data-testid="stSidebar"] .nav-label{font-family:var(--mono);
  font-size:.6rem !important; color:#C9D3C2 !important; text-transform:uppercase; letter-spacing:.15em; margin:2px 0 0;}
[data-testid="stSidebar"] .nav-label{margin:20px 0 6px;}
[data-testid="stSidebar"] .meta{font-family:var(--mono); font-size:.7rem !important; color:#C9D3C2 !important;
  line-height:1.8; margin:0;}
[data-testid="stSidebar"] .meta b{color:#F6F4EE !important; font-weight:500;}
[data-testid="stSidebar"] hr{border-color:rgba(246,244,238,.2);}
[data-testid="stSidebar"] .stButton>button{width:100%; justify-content:flex-start; text-align:left;
  background:transparent; border:none; border-left:3px solid transparent; border-radius:0;
  color:#E3E9DE; padding:6px 12px; font-size:.9rem;}
[data-testid="stSidebar"] .stButton>button:hover{background:rgba(246,244,238,.12); color:#fff;}
[data-testid="stSidebar"] .stButton>button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]{
  background:#F6F4EE; color:#262923; border-left:3px solid var(--clay); font-weight:600;}

.hero-wrap{text-align:left; padding:6px 0 18px; margin-bottom:14px; border-bottom:1px solid var(--line);}
.hero-wrap .wordmark{font-family:var(--serif) !important; font-size:3rem !important; font-weight:400 !important;
  margin:12px 0 2px !important; line-height:1.05 !important; color:var(--ink);}
.hero-wrap .tagline{font-family:var(--mono); color:var(--sage-d); letter-spacing:.2em; text-transform:uppercase;
  font-size:.68rem; margin:0 0 4px;}
.hero-wrap .sub{color:#4A4F44; max-width:560px; margin:12px 0 0; font-size:.97rem; line-height:1.65;}
.stat-row{display:flex; gap:8px; flex-wrap:wrap; margin-top:16px;}
.stat{border:1px solid var(--line); background:#fff; border-radius:3px; padding:4px 10px;
  font-family:var(--mono); font-size:.7rem; color:var(--muted);} .stat b{color:var(--ink); font-weight:500;}
.feat{border-top:1px solid var(--ink); padding:12px 2px 4px; min-height:100px;}
.feat h4{margin:8px 0 4px; font-size:.98rem;} .feat p{margin:0; color:var(--muted); font-size:.84rem; line-height:1.55;}
.live{display:inline-flex; align-items:center; gap:7px; font-family:var(--mono); font-size:.66rem;
  color:var(--muted); letter-spacing:.14em; text-transform:uppercase;}
.live i{width:7px; height:7px; border-radius:50%; background:var(--sage);}
@media (max-width:900px){[data-testid="stMain"] .block-container{margin:.4rem; padding:1.2rem 1rem;}}
@media (prefers-reduced-motion:reduce){*{animation:none !important; transition:none !important;}}
</style>
"""


def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)
    axis = dict(gridcolor="#E8E5DA", linecolor=LINE, zerolinecolor=LINE, tickfont=dict(family=MONO, size=11),
                title=dict(font=dict(family=SANS, size=12, color=MUTED)))
    pio.templates["editorial"] = go.layout.Template(layout=dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, family=SANS, size=12),
        colorway=[SAGE_D, SAGE, CLAY, "#A9B59F", "#8B8A7A"],
        xaxis=axis, yaxis=axis, bargap=0.35,
        legend=dict(font=dict(color=INK, size=11), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE, font=dict(color=INK, family=MONO, size=12)),
        title=dict(font=dict(family=SANS, size=14, color=INK)),
        margin=dict(l=20, r=20, t=50, b=30),
    ))
    pio.templates.default = "editorial"