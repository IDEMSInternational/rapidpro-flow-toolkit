import networkx as nx
import tablib

# from .sheetparser import SheetParser


class RowDataSheet:
    def __init__(self, row_parser, rows):
        """
        Args:
          rows: a list of RowModel instances
          row_parser: parser to use for converting rows to flat dicts.
        """
        self.row_parser = row_parser
        self.rows = rows

    # def from_file(row_parser, context, filename, file_format='csv'):
    #     sheet_parser = SheetParser(row_parser, context, filename, file_format)
    #     return sheet_parser.get_row_data_sheet()

    def export(self, filename, file_format="csv"):
        """
        Export a list of RowModel instances to file.

        Args:
            filename: destination filename
            format: Export file format.
                Supported file formats as supported by tablib,
                see https://tablib.readthedocs.io/en/stable/formats.html
        """
        data = self.convert_to_tablib()
        exported_data = data.export(file_format)
        write_type = "w" if type(exported_data) == str else "wb"
        with open(filename, write_type) as f:
            f.write(exported_data)

    def convert_to_tablib(self):
        """
        Convert a list of RowModel instances to tablib.Dataset.

        Return:
          A tablib.Dataset representation of the data.
        """

        data = tablib.Dataset()
        data.headers = self._get_headers()
        for row in self.rows:
            row_dict = self.row_parser.unparse_row(row)
            data.append([row_dict.get(header, "") for header in data.headers])
        return data

    def _get_headers(self):
        """
        Get an ordered list of column headers.
        Each row contains a subset of the final set of column headers.
        These subsets need to be merged while respecting the relative order
        within each row. Note: The resulting set of headers is unique,
        however, their order is not guaranteed to be unique.
        TODO: A better approach would be to use the DataModel of the rows
        to uniquely infer the order of the headers.
        Return:
            A list of strings representing the column headers of the sheet.
        """

        # Create a graph (representing a poset) whose nodes are the column headers,
        # and whose edges A -> B represent that column header A should come before
        # column header B.
        header_graph = nx.DiGraph()
        for row in self.rows:
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
