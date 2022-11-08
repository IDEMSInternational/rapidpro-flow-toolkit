from collections import defaultdict, OrderedDict
import networkx as nx

class SheetParser:

    def __init__(self, row_parser):
        self.output = None  # Gets reinitialized with each call to parse
        self.row_parser = row_parser

    def parse(self, sheet):
        pass

    def unparse(self, rows):
        # Args:
        #   rows: a list of RowModel instances
        # Return:
        #   a sheet (TODO: Tablib?)
        pass

    def get_headers(self, rows):
        # Get an ordered list of column headers.
        # Each row contains a subset of the final set of column headers.
        # These subsets need to be merged while respecting the relative order
        # within each row. Note: The resulting set of headers is unique,
        # however, their order is not guaranteed to be unique.
        # TODO: A better approach would be to use the DataModel of the rows
        # to uniquely infer the order of the headers.
        # Args:
        #   rows: a list of RowModel instances
        # Return:
        #   a list of strings representing the column headers of the sheet

        # Create a graph (representing a poset) whose nodes are the column headers,
        # and whose edges A -> B represent that column header A should come before
        # column header B.
        header_graph = nx.DiGraph()
        for row in rows:
            row_dict = self.row_parser.unparse_row(row)
            k_prev = None
            # For each pair of consecutive headers in this row, add an edge.
            for k, _ in row_dict.items():
                if k_prev:
                    header_graph.add_edge(k_prev, k)
                k_prev = k

        # We now get a linear order of our headers from this poset graph
        # by doing a topological sort.
        try:
            ordering = list(nx.topological_sort(header_graph))
        except nx.exception.NetworkXUnfeasible:
            raise ValueError("Inconsistent ordering of headers in provided rows.")
        return ordering
