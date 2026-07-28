# backend/critical_path.py
import json

def compute_dag_longest_path(task_ids, adj, in_degree, weights):
    """
    Computes the longest path (critical path) in a DAG using dynamic programming.
    
    Args:
        task_ids (list): List of all task IDs in the DAG.
        adj (dict): Adjacency list mapping task_id -> list of successor task_ids.
        in_degree (dict): In-degree map mapping task_id -> number of predecessor tasks.
        weights (dict): Weight map mapping task_id -> dict with "total" weight.
        
    Returns:
        tuple: (path_ids, path_edges)
            path_ids (list): List of task IDs on the critical path in execution order.
            path_edges (list of lists): List of [from_id, to_id] edges on the critical path.
    """
    if not task_ids or not weights:
        return [], []

    memo = {}
    next_node = {}

    def get_longest_path_from(node_id):
        if node_id in memo:
            return memo[node_id]

        max_weight = 0.0
        best_child = None
        
        # Iterate over successors
        successors = adj.get(node_id, [])
        for child_id in successors:
            child_weight = get_longest_path_from(child_id)
            if child_weight > max_weight:
                max_weight = child_weight
                best_child = child_id

        node_total_weight = weights.get(node_id, {}).get("total", 0.0)
        memo[node_id] = node_total_weight + max_weight
        next_node[node_id] = best_child
        return memo[node_id]

    # Find root nodes (in_degree == 0)
    roots = [node_id for node_id in task_ids if in_degree.get(node_id, 0) == 0]
    if not roots:
        # If circular or invalid, fallback to using all nodes
        roots = task_ids

    longest_path_weight = -1.0
    best_root = None
    for r in roots:
        w = get_longest_path_from(r)
        if w > longest_path_weight:
            longest_path_weight = w
            best_root = r

    # Reconstruct path
    path = []
    curr = best_root
    while curr is not None:
        path.append(curr)
        curr = next_node.get(curr)

    # Construct edges
    edges = []
    for i in range(len(path) - 1):
        edges.append([path[i], path[i+1]])

    return path, edges
