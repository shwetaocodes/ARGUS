import networkx as nx
from sqlalchemy.orm import Session
from app.models.entity_relationship import EntityRelationship
from app.models.event_entity import EventEntity
from app.services.graph_analysis import get_entity_neighborhood
from app.models.entity import Entity


def build_graph(db: Session) -> nx.Graph:
    G = nx.Graph()
    rels = db.query(EntityRelationship).all()
    for r in rels:
        G.add_edge(r.entity_a_id, r.entity_b_id, weight=r.co_occurrence_count)
    return G


def compute_centrality(db: Session, top_n: int = 20) -> dict:
    G = build_graph(db)
    if G.number_of_nodes() == 0:
        return {"degree": [], "betweenness": [], "eigenvector": []}

    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, weight="weight")

    try:
        eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=500)
    except nx.PowerIterationFailedConvergence:
        eigenvector = {}  

    def top_entities(scores: dict, n: int):
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]
        result = []
        for entity_id, score in top:
            entity = db.query(Entity).filter(Entity.id == entity_id).first()
            if entity:
                result.append({"entity_id": entity.id, "name": entity.name, "score": round(score, 4)})
        return result

    return {
        "degree": top_entities(degree, top_n),
        "betweenness": top_entities(betweenness, top_n),
        "eigenvector": top_entities(eigenvector, top_n) if eigenvector else [],
    }


def get_entity_neighborhood(db: Session, entity_id: int, depth: int = 1) -> dict:
    """Returns nodes/edges for the local subgraph around one entity — feeds a graph viz on the frontend."""
    G = build_graph(db)
    if entity_id not in G:
        return {"nodes": [], "edges": []}

    nodes_in_range = {entity_id}
    frontier = {entity_id}
    for _ in range(depth):
        next_frontier = set()
        for node in frontier:
            next_frontier |= set(G.neighbors(node))
        nodes_in_range |= next_frontier
        frontier = next_frontier

    subgraph = G.subgraph(nodes_in_range)
    entities = {e.id: e for e in db.query(Entity).filter(Entity.id.in_(nodes_in_range)).all()}

    return {
        "nodes": [{"id": n, "name": entities[n].name, "type": entities[n].type.value} for n in subgraph.nodes if n in entities],
        "edges": [{"source": u, "target": v, "weight": d["weight"]} for u, v, d in subgraph.edges(data=True)],
    }

def enrich_with_entity_context(db: Session, event_ids: list[int]) -> list[dict]:
    """For detection evidence — surface which entities tie these events together."""
    entity_ids = set()
    for eid in event_ids:
        links = db.query(EventEntity).filter(EventEntity.event_id == eid).all()
        entity_ids.update(l.entity_id for l in links)

    return [get_entity_neighborhood(db, eid, depth=1) for eid in entity_ids]