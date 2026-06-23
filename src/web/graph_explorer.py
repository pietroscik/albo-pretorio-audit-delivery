import streamlit as st
import streamlit.components.v1 as components
import networkx as nx
from pyvis.network import Network
from pathlib import Path

st.set_page_config(layout="wide", page_title="Knowledge Graph Navigator", page_icon="🕸️")

st.title("🕸️ Navigatore Grafo di Conoscenza (Knowledge Graph)")
st.markdown("Esplora le relazioni tra Atti, Beneficiari, RUP e Capitoli di Spesa.")

@st.cache_data
def load_graph():
    gexf_path = Path("data/albo_download/report/knowledge_graph.gexf")
    if not gexf_path.exists():
        return None
    return nx.read_gexf(str(gexf_path))

G = load_graph()

if G is None:
    st.error("Grafo non trovato. Esegui la pipeline per generare il Knowledge Graph.")
    st.stop()

# Estrai i nodi per categoria per i filtri
rups = sorted([n for n, d in G.nodes(data=True) if d.get('type') == 'RUP'])
beneficiari = sorted([n for n, d in G.nodes(data=True) if d.get('type') == 'Beneficiario'])

st.sidebar.header("Filtri Grafo")
view_mode = st.sidebar.radio("Modalità di visualizzazione:", ["Grafo Completo (Lento)", "Filtra per RUP", "Filtra per Beneficiario"])

sub_g = G

if view_mode == "Filtra per RUP":
    selected_rup = st.sidebar.selectbox("Seleziona RUP:", rups)
    if selected_rup:
        # Crea un sotto-grafo estraendo i vicini fino a profondità 2
        nodes_to_keep = {selected_rup}
        for n1 in G.neighbors(selected_rup):
            nodes_to_keep.add(n1)
            for n2 in G.neighbors(n1):
                nodes_to_keep.add(n2)
        sub_g = G.subgraph(nodes_to_keep)

elif view_mode == "Filtra per Beneficiario":
    selected_ben = st.sidebar.selectbox("Seleziona Beneficiario:", beneficiari)
    if selected_ben:
        nodes_to_keep = {selected_ben}
        # Aggiungiamo anche i predecessori (gli atti che puntano a lui)
        for n1 in G.predecessors(selected_ben):
            nodes_to_keep.add(n1)
            # E chi gestisce l'atto
            for n2 in G.predecessors(n1):
                nodes_to_keep.add(n2)
            # E da che capitolo viene
            for n3 in G.successors(n1):
                nodes_to_keep.add(n3)
        sub_g = G.subgraph(nodes_to_keep)

# Impostiamo PyVis
net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)

# Personalizziamo i colori in base al tipo
color_map = {
    'Atto': '#97C2FC',
    'RUP': '#FF9999',
    'Beneficiario': '#FFCC99',
    'Capitolo': '#FFFF99',
    'CIG': '#CCFFCC'
}

for node, data in sub_g.nodes(data=True):
    node_type = data.get('type', 'Atto')
    color = color_map.get(node_type, '#97C2FC')
    
    # Costruiamo il titolo per l'hover
    title = f"Tipo: {node_type}\n"
    for k, v in data.items():
        if k != 'label':
            title += f"{k}: {v}\n"
            
    net.add_node(node, label=str(node)[:20], title=title, color=color)

for source, target, data in sub_g.edges(data=True):
    title = data.get('relation', '')
    if 'importo' in data:
        title += f" (€ {data['importo']})"
    net.add_edge(source, target, title=title)

# Opzioni fisiche per stabilizzare il grafo
net.set_options("""
var options = {
  "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "centralGravity": 0.01,
      "springLength": 100,
      "springConstant": 0.08
    },
    "maxVelocity": 50,
    "solver": "forceAtlas2Based",
    "timestep": 0.35,
    "stabilization": {"iterations": 150}
  }
}
""")

path_html = "data/albo_download/report/temp_graph.html"
net.save_graph(path_html)

with open(path_html, 'r', encoding='utf-8') as f:
    html_data = f.read()

components.html(html_data, height=750)
