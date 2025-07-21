import streamlit as st
from pyvis.network import Network
import networkx as nx
import streamlit.components.v1 as components

# 👉 Page configuration
st.set_page_config(layout="wide", page_title="X-RAY-VISION")

# 👉 Custom CSS
st.markdown("""
<style>
  .intro, .outro {
    text-align: center;
    font-size: 1.2rem;
    margin: 20px 0;
    color: #333333;
  }
  iframe { border: none; }
</style>
""", unsafe_allow_html=True)

# 👉 Top intro text
st.markdown('<div class="intro">🔍 <strong>Explore Your 4‑Hop Network</strong>: hover to see edge details, nodes locked in place.</div>', unsafe_allow_html=True)

# 👉 Build fixed linear 4-hop graph
pos = {i: (i * 300, 0) for i in range(1, 5)}
G = nx.DiGraph()
for i in pos:
    G.add_node(i, label=f"Hop {i}", title=f"Node info: Hop {i}")
edges = [(1,2,"green","15 ms"), (2,3,"orange","25 ms"), (3,4,"red","40 ms")]
for s,d,clr,tip in edges:
    G.add_edge(s, d, color=clr, title=tip)

net = Network(height="600px", width="100%", directed=True, notebook=False)
net.from_nx(G)
for node in net.nodes:
    x, y = pos[node["id"]]
    node.update({
        "x": x, "y": y,
        "fixed": True, "physics": False,
        "value": 100,
        "shape": "dot",
        "color": "#87CEEB",
        "label": node["label"],
        "title": node["title"],
    })
net.set_options("""
{
  "physics": { "enabled": false },
  "interaction": {
    "dragNodes": false,
    "dragView": false,
    "zoomView": false
  }
}
""")
html = net.generate_html()

# 👉 Centered graph container
with st.container():
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        components.html(html, height=650)

# 👉 Bottom outro text
st.markdown('<div class="outro">✨ Nodes fixed in a row, edges colored by delta times. Next: upload CSV to autogenerate!</div>', unsafe_allow_html=True)
