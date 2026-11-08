from typing import List, Dict, Tuple, Any, Set, Optional

from networkx.algorithms import (
    moral, is_chordal,
    complete_to_chordal_graph,
    chordal_graph_cliques
)

from collections import defaultdict
from functools import reduce
from copy import deepcopy
from pprint import pprint

import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
import itertools
import random
import numpy as np


def almost_equal(x: float, y: float, threshold: float = 1e-6) -> bool:
    return abs(x-y) < threshold


def factor_crossjoin(f1: pd.DataFrame, f2: pd.DataFrame, how: str = "outer", **kwargs) -> pd.DataFrame:
    """
        Make a cross join (cartesian product) between two dataframes by using a constant temporary key.
        Also sets a MultiIndex which is the cartesian product of the indices of the input dataframes.
        See: https://github.com/pydata/pandas/issues/5401
        :param f1 first factor represented as a pandas DataFrame
        :param f2 second factor represented as a pandas DataFrame
        :param how type of the join to perform on factors - for the crossjoin the default is "outer"
        :param kwargs keyword arguments that will be passed to pd.merge()
        :return cross join of f1 and f2
        """
    f1['_tmpkey'] = 1
    f2['_tmpkey'] = 1

    res = pd.merge(f1.reset_index(), f2.reset_index(), on='_tmpkey', how=how, **kwargs).drop('_tmpkey', axis=1)
    res = res.set_index(keys=f1.index.names + f2.index.names)

    f1.drop('_tmpkey', axis=1, inplace=True)
    f2.drop('_tmpkey', axis=1, inplace=True)

    return res


def divide_factors(f1: pd.DataFrame, f2: pd.DataFrame) -> pd.DataFrame:
    f1_vars = f1.index.names
    f2_vars = f2.index.names

    common_vars = [v for v in f1_vars if v in f2_vars]

    if not common_vars:
        ### we have to do a cross join
        f_res = factor_crossjoin(f1, f2)
        f_res["prob"] = f_res["prob_x"] / f_res["prob_y"]
        f_res = f_res.drop(columns=["prob_x", "prob_y"])

    else:
        ### there is a set of common vars, so we merge on them
        disjoint_vars = [v for v in f1_vars if v not in f2_vars] + [v for v in f2_vars if v not in f1_vars]
        f_res = pd.merge(f1.reset_index(), f2.reset_index(), on=common_vars, how="inner")\
            .set_index(keys=disjoint_vars + common_vars)
        f_res["prob"] = f_res["prob_x"] / f_res["prob_y"]
        f_res = f_res.drop(columns=["prob_x", "prob_y"])

    return f_res


def multiply_factors(f1: pd.DataFrame, f2: pd.DataFrame) -> pd.DataFrame:
    f1_vars = f1.index.names
    f2_vars = f2.index.names

    common_vars = [v for v in f1_vars if v in f2_vars]

    if not common_vars:
        ### we have to do a cross join
        f_res = factor_crossjoin(f1, f2)
        f_res["prob"] = f_res["prob_x"] * f_res["prob_y"]
        f_res = f_res.drop(columns=["prob_x", "prob_y"])

    else:
        ### there is a set of common vars, so we merge on them
        disjoint_vars = [v for v in f1_vars if v not in f2_vars] + [v for v in f2_vars if v not in f1_vars]
        f_res = pd.merge(f1.reset_index(), f2.reset_index(), on=common_vars, how="inner")\
            .set_index(keys=disjoint_vars + common_vars)
        f_res["prob"] = f_res["prob_x"] * f_res["prob_y"]
        f_res = f_res.drop(columns=["prob_x", "prob_y"])

    return f_res


def absorption(
    factor: pd.DataFrame,
    projection: pd.DataFrame or float,
    old_projection: pd.DataFrame or float
) -> pd.DataFrame:

    res = factor

    if isinstance(projection, pd.DataFrame):
        res = multiply_factors(factor, projection)
    else:
        res *= projection

    if isinstance(old_projection, pd.DataFrame):
        return divide_factors(res, old_projection)

    return res / old_projection


def sumout(f:pd.DataFrame, vars: List[str]) -> pd.DataFrame or float:
    f_vars = f.index.names
    remaining_vars = [v for v in f_vars if v not in vars]

    if remaining_vars:
        return f.groupby(level=remaining_vars).sum()
    else:
        # if we are summing out all values return the sum of all entries
        return f["prob"].sum()


def normalize(f:pd.DataFrame) -> pd.DataFrame:
    f["prob"] = f["prob"] / f["prob"].sum()
    return f


class Factor:
    """
    Place holder class for a Factor in a factor graph (implicitly also within a junction tree)
    """
    def __init__(self, vars: List[str], table: pd.DataFrame):
        """
        Instantiate a factor
        :param vars: random variables of a factor
        :param table: factor table that is proportional to probabilities
        """
        self.vars = vars
        self.table = table



class BayesNode:
    def __init__(self,
                 var_name: str = None,
                 parent_nodes: List["BayesNode"] = None,
                 cpd: pd.DataFrame = None):
        """
        Defines a binary random variable in a bayesian network by
        :param var_name: the random variable name
        :param parent_nodes: the parent random variables (conditioning variables)
        :param cpd: the conditional probability distribution given in the form of a Pandas Dataframe which has a
        multilevel index that contains all possible binary value combinations for the random variable and its parents

        An example CPD is:
                   prob
            c a b
            1 1 1  0.946003
                0  0.080770
              0 1  0.664979
                0  0.223632
            0 1 1  0.751246
                0  0.355359
              0 1  0.688208
                0  0.994031

        The first level of the index is always the `var_name` random variable (the one for the current node)
        The next levels in the index correspond to the parent random variables
        """
        self.var_name = var_name
        self.parent_nodes = parent_nodes
        self.cpd = cpd

    def to_factor(self) -> Factor:
        factor_vars = [self.var_name] + [p.var_name for p in self.parent_nodes]
        return Factor(vars=factor_vars, table=self.cpd.copy(deep=True))

    def pretty_print(self):
        res = ""
        res += "Node(%s" % self.var_name
        if self.parent_nodes:
            res += " | "
            for p in [p.var_name for p in self.parent_nodes]:
                res += p + " "
            res += ")"
        else:
            res += ")"

        res += "\n"
        res += str(self.cpd)
        res += "\n"

        return res

    def __str__(self):
        res = ""
        res += "Node(%s" % self.var_name
        if self.parent_nodes:
            res += " | "
            for p in [p.var_name for p in self.parent_nodes]:
                res += p + " "
            res += ")"
        else:
            res += ")"

        return res

    def __repr__(self):
        return self.__str__()


class BayesNet:
    """
    Representation for a Bayesian Network
    """
    def __init__(self, bn_file: str="data/bnet"):
        # nodes are indexed by their variable name
        self.nodes, self.queries = BayesNet.parse(bn_file)

    @staticmethod
    def _create_cpd(var: str, parent_vars: List[str], parsed_cpd: List[float]) -> pd.DataFrame:
        num_parents = len(parent_vars) if parent_vars else 0
        product_list = [[1, 0]] + [[0, 1]] * num_parents

        cpt_idx = list(itertools.product(*product_list))
        cpt_vals = parsed_cpd + [(1 - v) for v in parsed_cpd]

        idx_names = [var]
        if parent_vars:
            idx_names.extend(parent_vars)

        index = pd.MultiIndex.from_tuples(cpt_idx, names=idx_names)
        cpd_df = pd.DataFrame(data=cpt_vals, index=index, columns=["prob"])

        return cpd_df


    @staticmethod
    def parse(file: str) -> Tuple[Dict[str, BayesNode], List[Dict[str, Any]]]:
        """
        Parses the input file and returns an instance of a BayesNet object
        :param file:
        :return: the BayesNet object
        """
        bn_dict: Dict[str, BayesNode] = {}
        query_list: List[Dict[str, Any]] = []

        with open(file) as fin:
            # read the number of vars involved
            # and the number of queries
            N, M = [int(x) for x in next(fin).split()]

            # read the vars, their parents and the CPD
            for i in range(N):
                line = next(fin).split(";")
                parsed_var = line[0].strip()
                parsed_parent_vars = line[1].split()
                parsed_cpd = [float(v) for v in line[2].split()]

                parent_vars = [bn_dict[v] for v in parsed_parent_vars]
                cpd_df = BayesNet._create_cpd(parsed_var, parsed_parent_vars, parsed_cpd)
                bn_dict[parsed_var] = BayesNode(var_name=parsed_var, parent_nodes=parent_vars, cpd=cpd_df)

            # read the queries
            for i in range(M):
                queries, conds = next(fin).split('|')

                query_vars = queries.split()
                query_vars_dict = dict([(q.split("=")[0], q.split("=")[1]) for q in query_vars])

                cond_vars = conds.split()
                cond_vars_dict = dict([(c.split("=")[0], c.split("=")[1]) for c in cond_vars])

                query_list.append({
                    "query": query_vars_dict,
                    "cond": cond_vars_dict
                })

            # read the answers
            for i in range(M):
                query_list[i]["answer"] = float(next(fin).strip())

        return bn_dict, query_list

    def get_graph(self) -> nx.DiGraph:
        bn_graph = nx.DiGraph()

        # add nodes with random var attributes that relate the node name to the BayesNode instance
        # in the bayesian network
        for n in self.nodes:
            bn_graph.add_node(n, bn_var=self.nodes[n])

        # add edges
        for n in self.nodes:
            parent_vars = [v.var_name for v in self.nodes[n].parent_nodes]
            if parent_vars:
                for v in parent_vars:
                    bn_graph.add_edge(v, n)

        return bn_graph

    def prob(self, var_name: str, parent_values: List[int] = None) -> float:
        """
        Function that will get the probability value for the case in which the `var_name' variable is True
        (var_name = 1) and the parent values are given by the list `parent values'
        :param var_name: the variable in the bayesian network for which we are determining the conditional property
        :param parent_values: The list of parent values. Is None if var_name has no parent variables.
        :return:
        """
        if parent_values is None:
            parent_values = []

        index_line = tuple([1] + parent_values)

        return self.nodes[var_name].cpd.loc[index_line]["prob"]

    def sample_log_prob(self, sample: Dict[str, int]):
        logprob = 0
        for var_name in self.nodes:
            var_value = sample[var_name]
            parent_vals = None
            if self.nodes[var_name].parent_nodes:
                parent_names = [parent.var_name for parent in self.nodes[var_name].parent_nodes]
                parent_vals = [sample[pname] for pname in parent_names]

            prob = self.prob(var_name, parent_vals)
            if var_value == 0:
                prob = 1 - prob

            logprob += np.log(prob)

        return logprob

    def sample(self) -> Dict[str, int]:
        """
        Sample values for all the variables in the bayesian network and return them as a dictionary
        :return: A dictionary of var_name, value pairs
        """
        values = {}
        remaining_vars = [var_name for var_name in self.nodes]

        while remaining_vars:
            new_vars = []
            for var_name in remaining_vars:
                parent_vars = [p.var_name for p in self.nodes[var_name].parent_nodes]
                if all(p in values for p in parent_vars):
                    parent_vals = [values[p] for p in parent_vars]
                    prob = self.prob(var_name, parent_vals)
                    values[var_name] = int(np.random.sample() <= prob)
                else:
                    new_vars.append(var_name)
            remaining_vars = new_vars
        return values

    def pretty_print(self):
        res = "Bayesian Network:\n"
        for var_name in self.nodes:
            res += self.nodes[var_name].pretty_print() + "\n"

        return res

    def __str__(self):
        res = "Bayesian Network:\n"
        for var_name in self.nodes:
            res += str(self.nodes[var_name]) + "\n"

        return res

    def __repr__(self):
        return self.__str__()


class JunctionTree:
    """
    Place holder class for the JunctionTree algorithm
    """
    def __init__(self, bn: BayesNet):
        self.bn = bn
        self.clique_tree = self._get_clique_tree()
        self.messages = None
        self.uncalibrated_jt = None

    def _moralize_graph(self, g: nx.DiGraph) -> nx.Graph:
        return moral.moral_graph(g)

    def _triangulate(self, h: nx.Graph) -> nx.Graph:
        chordal_graph, _ = complete_to_chordal_graph(h)
        return chordal_graph

    def _create_clique_graph(self, th: nx.Graph) -> nx.Graph:
        assert is_chordal(th), "Given Graph is not chordal"

        # Get the maximum cliques of a chordal graph
        cliques = [tuple(sorted(clique)) for clique in chordal_graph_cliques(th)]

        clique_graph = nx.Graph()
        clique_graph.add_nodes_from(cliques, type="clique")

        for clique1, clique2 in itertools.combinations(cliques, 2):
            set_clique1 = set(clique1)
            set_clique2 = set(clique2)

            if set_clique1.isdisjoint(set_clique2):
                continue

            edge = tuple(sorted(set_clique1.intersection(set_clique2)))
            clique_graph.add_edge(clique1, clique2, weight=len(edge), sepset=edge)

        return clique_graph

    def _extract_clique_tree(self, c: nx.Graph) -> nx.Graph:
        return nx.maximum_spanning_tree(c, algorithm="kruskal")

        # This code can be used to display the clique tree
        # with the associated sepsets added as nodes in the graph

        # for edge in list(clique_tree.edges(data=True)):
        #     clique1, clique2, node = edge[0], edge[1], edge[2]["sepset"]

        #     clique_tree.add_node(node, type="sepset")
        #     clique_tree.add_edge(clique1, node)
        #     clique_tree.add_edge(clique2, node)
        #     clique_tree.remove_edge(clique1, clique2)

        # return clique_tree

    def _get_clique_tree(self) -> nx.Graph:
        """
        Generate the clique tree which is used to propagate "messages" (run belief propagation)
        within the cliques to balance the clique tree
        :return: The CliqueTree as a nx.DiGraph where each node has an attribute called "factor_vars", which
        is the list of random variables within the clique.
        """
        g = self.bn.get_graph()

        #  see https://networkx.org/documentation/stable/_modules/networkx/algorithms/moral.html
        h = self._moralize_graph(g)

        th = self._triangulate(h)

        #   see https://networkx.org/documentation/stable/reference/algorithms/chordal.html
        c = self._create_clique_graph(th)

        #   see https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.tree.mst.maximum_spanning_tree.html#networkx.algorithms.tree.mst.maximum_spanning_tree
        t = self._extract_clique_tree(c)

        return t


    def draw(self) -> None:
        """
        Draw the clique tree using nx.draw. Each node is labeled with the variables of its clique,
        and each edge is labeled with the sepset of the two cliques it connects.
        Nodes can be dragged with the mouse to pull overlapping cliques apart.
        """
        pos = nx.spring_layout(self.clique_tree, seed=42)
        node_labels = {clique: ", ".join(clique) for clique in self.clique_tree.nodes()}
        edge_labels = {
            (c1, c2): ", ".join(sepset)
            for c1, c2, sepset in self.clique_tree.edges(data="sepset")
        }

        fig, ax = plt.subplots(figsize=(10, 8))

        def redraw():
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            ax.clear()
            ax.set_title("Junction Tree")
            nx.draw(self.clique_tree, pos, ax=ax, labels=node_labels, with_labels=True, font_weight='bold',
                    node_color="lightblue", node_size=2500, font_size=9)
            nx.draw_networkx_edge_labels(self.clique_tree, pos, ax=ax, edge_labels=edge_labels,
                                         font_color="red", font_size=8)
            if dragged["node"] is not None:
                # keep the view fixed while dragging, otherwise autoscaling makes the plot jump
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
            ax.axis("off")
            fig.canvas.draw_idle()

        dragged = {"node": None}

        def on_press(event):
            if event.inaxes != ax:
                return
            # pick the node closest to the click (in pixels), if the click falls inside its circle
            to_pixels = ax.transData.transform
            node, dist = min(
                ((n, ((to_pixels(p) - (event.x, event.y)) ** 2).sum() ** 0.5) for n, p in pos.items()),
                key=lambda nd: nd[1],
            )
            if dist < 25 * fig.dpi / 72:  # node_size=2500 pt^2 -> radius of 25 pt
                dragged["node"] = node

        def on_motion(event):
            if dragged["node"] is None or event.inaxes != ax:
                return
            pos[dragged["node"]] = (event.xdata, event.ydata)
            redraw()

        def on_release(event):
            dragged["node"] = None

        fig.canvas.mpl_connect("button_press_event", on_press)
        fig.canvas.mpl_connect("motion_notify_event", on_motion)
        fig.canvas.mpl_connect("button_release_event", on_release)

        redraw()
        plt.show()


    def _load_factors(self) -> None:
        """
        Compute initial node potentials, by loading the factors from the original bayesian network.
        Each factor from the original bayesian network is assigned to a **single** node in the clique tree,
        with the condition that **all** factor vars be included in the clique node vars.
        """
        for clique in self.clique_tree.nodes:
            factor_vars = list(clique)
            assignments = itertools.product([0, 1], repeat=len(factor_vars))
            index = pd.MultiIndex.from_tuples(assignments, names=factor_vars)
            self.clique_tree.nodes[clique]["factor_vars"] = factor_vars
            self.clique_tree.nodes[clique]["factor"] = pd.DataFrame(
                {"prob": 1.0}, index=index
            )

        for node in self.bn.nodes.values():
            factor = node.to_factor()
            factor_vars = set(factor.vars)
            containing_cliques = [
                clique
                for clique in self.clique_tree.nodes
                if factor_vars.issubset(clique)
            ]
            if not containing_cliques:
                raise ValueError(
                    f"No clique contains the factor variables {sorted(factor_vars)}"
                )

            clique = min(containing_cliques, key=lambda candidate: (len(candidate), candidate))
            clique_node = self.clique_tree.nodes[clique]
            combined_factor = multiply_factors(
                clique_node["factor"], factor.table.copy(deep=True)
            )
            clique_node["factor"] = combined_factor.reorder_levels(
                clique_node["factor_vars"]
            )

    
    def _get_junction_tree(self, root_name: str = None) -> nx.DiGraph:
        """
        Set a direction to the edges of the clique tree (which is an nx.Graph) such that the Junction Tree has
        a root. The root node is given by root_name.
        :param root_name: The name of the clique node that is the root of the Junction Tree
        :return: a nx.DiGraph representing the Junction Tree
        """
        if root_name is None or root_name not in self.clique_tree:
            print("Selected root node %s not in clique tree. Choosing randomly." % root_name)
            root_name = random.choice(list(self.clique_tree.nodes()))

        t: nx.DiGraph = nx.bfs_tree(self.clique_tree, root_name)
        clique_tree_attrs = deepcopy(dict(self.clique_tree.nodes(data=True)))
        nx.set_node_attributes(t, clique_tree_attrs)

        return t


    def _incorporate_evidence(self, jt: nx.DiGraph, evidence: Dict[str, int]) -> nx.DiGraph:

    # TODO
        """
        Incorporate the evidence. For each variable in the `evidence' dictionary, choose **one** node of the
        Junction Tree and reduce the factor table (pd.DataFrame) of that node to the set of value combinations (index)
        matching the value of the observed evidence variable.
        :param jt: the initial uncalibrated Junction Tree with factors loaded from the original bayesian network
        :param evidence: a dictionary of observed variables

        :return: The uncalibrated junction tree with incorporated evidence
        """


        for var, value in evidence.items():
            value = int(value)
            if var not in self.bn.nodes or value not in (0, 1):
                raise ValueError(f"Invalid evidence: {var}={value}")
            clique = next((c for c in jt if var in jt.nodes[c]["factor_vars"]), None)
            if clique is None:
                raise ValueError(f"No clique contains evidence variable {var}")
            factor = jt.nodes[clique]["factor"]
            jt.nodes[clique]["factor"] = factor[
                factor.index.get_level_values(var) == value
            ]
        return jt
    

    def _run_belief_propagation(self, uncalibrated_jt: nx.DiGraph, root_name: str) -> nx.DiGraph:
        """
        Run the upward and downward passes in the Belief propagation algorithm to calibrate
        :param uncalibrated_jt: The uncalibrated Junction Tree obtained after incorporating the evidence
        :return: The calibrated Junction tree
        """

        # TODO
        if root_name not in uncalibrated_jt:
            raise ValueError(f"Root clique {root_name} is not in the junction tree")

        for parent, child in uncalibrated_jt.edges:
            separator = sorted(set(parent) & set(child))
            uncalibrated_jt.edges[parent, child]["sepset"] = separator

        for child in list(nx.dfs_postorder_nodes(uncalibrated_jt, root_name)):
            parents = list(uncalibrated_jt.predecessors(child))
            if not parents:
                continue
            parent = parents[0]
            separator = uncalibrated_jt.edges[parent, child]["sepset"]
            projection = sumout(
                uncalibrated_jt.nodes[child]["factor"],
                [v for v in uncalibrated_jt.nodes[child]["factor_vars"] if v not in separator],
            )
            uncalibrated_jt.edges[parent, child]["upward_message"] = deepcopy(projection)
            parent_vars = uncalibrated_jt.nodes[parent]["factor_vars"]
            uncalibrated_jt.nodes[parent]["factor"] = absorption(
                uncalibrated_jt.nodes[parent]["factor"], projection, 1.0
            ).reorder_levels(parent_vars)

        for parent, child in nx.bfs_edges(uncalibrated_jt, root_name):
            separator = uncalibrated_jt.edges[parent, child]["sepset"]
            projection = sumout(
                uncalibrated_jt.nodes[parent]["factor"],
                [v for v in uncalibrated_jt.nodes[parent]["factor_vars"] if v not in separator],
            )
            child_vars = uncalibrated_jt.nodes[child]["factor_vars"]
            uncalibrated_jt.nodes[child]["factor"] = absorption(
                uncalibrated_jt.nodes[child]["factor"],
                projection,
                uncalibrated_jt.edges[parent, child]["upward_message"],
            ).reorder_levels(child_vars)

        return uncalibrated_jt


    def _eval_query(self, calibrated_jt: nx.DiGraph, query: Dict[str, int]) -> float:
        
        raise NotImplementedError("Not implemented by student")


    
    def _eval_query(self, calibrated_jt: nx.DiGraph,
                    query: Dict[str, int]) -> float:

        query = {v: int(x) for v, x in query.items()}

        """
        Evaluate the query by distinguishing between within- or out-of-clique queries.
        :param calibrated_jt: The calibrated Junction Tree
        :return: the float value for the probability of the query
        """
        Q = set(query)

        if not Q:
            return 1.0

        tree = calibrated_jt.to_undirected()
        cliques = list(tree.nodes)

        # Find a subtree containing all query variables
        terminals = [next((c for c in cliques if v in c), None) for v in Q]
        if None in terminals:
            raise ValueError("Query variable not found in any clique")

        # Case 1: All query variables belong to one clique
        containing = [c for c in cliques if Q.issubset(c)]

        if containing:
            root = min(containing, key=len)
            result = calibrated_jt.nodes[root]["factor"].copy()
        else:
            # Case 2: Query variables span multiple cliques
            root = terminals[0]
            nodes = {root}

            for c in terminals[1:]:
                nodes.update(nx.shortest_path(tree, root, c))

            subtree = tree.subgraph(nodes)
            parents = dict(nx.bfs_predecessors(subtree, root))

            result = calibrated_jt.nodes[root]["factor"].copy()

            for c in nx.bfs_tree(subtree, root):
                if c == root:
                    continue

                beta = calibrated_jt.nodes[c]["factor"].copy()
                separator = set(c) & set(parents[c])
                mu = sumout(beta, [v for v in beta.index.names if v not in separator])

                phi = divide_factors(beta, mu)
                phi["prob"] = phi["prob"].replace([np.inf, -np.inf], 0).fillna(0)
                result = multiply_factors(result, phi)

        # Sum out variables that are not queried
        result = sumout(result, [v for v in result.index.names if v not in Q])

        # Normalize and retrieve the requested assignment
        result = normalize(result)
        key = tuple(query[v] for v in result.index.names)

        try:
            return float(result.loc[key[0] if len(key) == 1 else key, "prob"])
        except KeyError:
            return 0.0


    def run_query(self, query: Dict[str, int], evidence: Dict[str, int]) -> float:
        
        # select a non-None root
        # I don't exactly know why this would be needed, as the code already selects a root from the existing clique tree noodes
        root_name = random.choice(list(self.clique_tree.nodes()))
        while root_name is None:
            root_name = random.choice(list(self.clique_tree.nodes()))

        self._load_factors()

        # get junction tree copy
        jt = self._get_junction_tree(root_name=root_name)

        # incorporate evidence
        uncalibrated_jt = self._incorporate_evidence(jt, evidence)
        self.uncalibrated_jt = uncalibrated_jt

        # calibrate tree
        calibrated_jt = self._run_belief_propagation(uncalibrated_jt, root_name)

        return self._eval_query(calibrated_jt, query)

    def run_queries(self, queries: List[Dict[str, int]]) -> None:
        """
        Run queries.
        :param queries: queries in the original bayesian network
        """
        for query in queries:
            query_prob = self.run_query(query["query"], query["cond"])
            if almost_equal(query_prob, query["answer"]):
                print("Query %s OK. Answer is %.6f, given result is %.6f" % (str(query), query["answer"], query_prob))
            else:
                print("Query %s NOT OK. Answer is %.6f, given result is %.6f" % (str(query), query["answer"], query_prob))

    def _format_query(self, query: Dict[str, int]) -> str:
        """
        Format given query for better display
        {'query': {'C': '1', 'D': '0', 'E': '0'}, 'cond': {'B': '0', 'I': '0'}}
            query      | evidence
        -> C=1 D=0 E=0 | B=0 I=0

        :param query: The query to be formatted for display
        :return: The formmated query
        """
        _query = " ".join(f"{var}={val}" for var, val in query["query"].items())
        _cond  = " ".join(f"{var}={val}" for var, val in query["cond"].items())

        return f"{_query} | {_cond} "

    



if __name__ == "__main__":
    bn = BayesNet(bn_file="data/bnet")
    jt = JunctionTree(bn=bn)
    jt.draw()

    jt.run_queries(bn.queries)
